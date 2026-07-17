from __future__ import annotations

import select
import sys
import time
from pathlib import Path
from typing import Annotated

import typer

from psalter.application.dto import (
    PassageDetailDTO,
    PsalmLearningViewDTO,
    RecitationAssessmentDTO,
    RecitationSubmission,
)
from psalter.application.errors import (
    ArtifactCleanupFailedError,
    AudioArtifactInvalidError,
    AudioRecorderNotConfiguredError,
    AudioRecordingFailedError,
    InvalidLearningTransitionError,
    LearningSessionNotFoundError,
    NoActivePassageError,
    PassageNotFoundError,
    PersistenceConflictError,
    PsalmLearningPlanConflictError,
    PsalmNotFoundError,
    PsalmTranslationAmbiguousError,
    TranscriberNotConfiguredError,
    TranscriptEmptyError,
    TranscriptOutputMissingError,
    UnsupportedAudioPlatformError,
    WhisperExecutableNotFoundError,
    WhisperModelNotFoundError,
    WhisperProcessFailedError,
)
from psalter.bootstrap import Container, build_container
from psalter.cli.readiness import require_ready
from psalter.config import build_config
from psalter.domain.learning import LearningPhase
from psalter.domain.passage import PassageKind
from psalter.domain.psalm import PsalmLearningStatus
from psalter.domain.recitation import RecitationResult, RecitationSource


def register(app: typer.Typer) -> None:
    @app.command("learn")
    def learn_command(
        psalm_number: int,
        translation_id: Annotated[str | None, typer.Option("--translation-id")] = None,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        require_ready(container)
        try:
            container.psalm_learning_service.begin_or_resume(
                psalm_number=psalm_number,
                translation_id=translation_id,
            )
        except (
            PsalmNotFoundError,
            PsalmTranslationAmbiguousError,
            NoActivePassageError,
            PsalmLearningPlanConflictError,
        ) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        while True:
            try:
                view = container.psalm_learning_service.get_learning_view(
                    psalm_number=psalm_number,
                    translation_id=translation_id,
                )
            except (
                PsalmNotFoundError,
                PsalmTranslationAmbiguousError,
                NoActivePassageError,
            ) as exc:
                typer.secho(str(exc), fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1) from exc

            if _render_completed_states(view):
                return

            active = view.active_passage
            if active is None:
                typer.secho("No active passage is available.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            session = container.learning_service.get_current_session(active.id)
            if session is None:
                typer.secho("Learning session was not initialized.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

            _print_header(view, active)
            if session.phase is LearningPhase.EXPOSURE:
                typer.echo("")
                typer.echo(active.canonical_text)
                prompt = (
                    "Read the complete Psalm, then continue to recitation?"
                    if active.kind is PassageKind.CONSOLIDATION
                    else "Read attentively, then continue to practice?"
                )
                if not typer.confirm(prompt, default=True):
                    return
                try:
                    if active.kind is PassageKind.CONSOLIDATION:
                        container.learning_service.complete_exposure_and_mark_ready(active.id)
                    else:
                        container.learning_service.complete_exposure(active.id)
                except InvalidLearningTransitionError as exc:
                    typer.secho(str(exc), fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1) from exc
                continue

            if session.phase is LearningPhase.PRACTICE:
                practice = container.learning_service.get_practice_view(active.id)
                typer.echo("")
                typer.echo(practice.masked_text)
                if not typer.confirm(
                    f"Complete practice level {practice.level}?",
                    default=True,
                ):
                    return
                try:
                    container.learning_service.complete_practice_level(active.id)
                except InvalidLearningTransitionError as exc:
                    typer.secho(str(exc), fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1) from exc
                continue

            if session.phase is LearningPhase.READY_FOR_RECITATION:
                assessment = _run_recitation(container, active)
                _print_assessment(assessment)
                if (
                    assessment.result is RecitationResult.PASS
                    and assessment.remaining_successes_required == 0
                ):
                    try:
                        updated_view = (
                            container.psalm_learning_service.advance_after_passage_learned(
                                view.psalm.id
                            )
                        )
                    except (
                        NoActivePassageError,
                        PsalmLearningPlanConflictError,
                    ) as exc:
                        typer.secho(str(exc), fg=typer.colors.RED, err=True)
                        raise typer.Exit(code=1) from exc
                    if active.kind is PassageKind.CONSOLIDATION:
                        typer.echo("Whole Psalm learned. Use `psalter review` for due reviews.")
                        if updated_view.plan.status is PsalmLearningStatus.LEARNED:
                            return
                    else:
                        typer.echo("Section learned.")
                        if (
                            updated_view.plan.status is PsalmLearningStatus.CONSOLIDATING
                            and updated_view.active_passage is not None
                            and updated_view.active_passage.kind is PassageKind.CONSOLIDATION
                        ):
                            typer.echo("All sections learned. Entering whole-Psalm consolidation.")
                        elif updated_view.active_passage is not None:
                            typer.echo(
                                f"Advancing to {_section_label(updated_view.active_passage)}."
                            )
                    if _render_completed_states(updated_view):
                        return
                    continue
                if assessment.result is RecitationResult.PASS:
                    typer.echo("Successful recitation recorded. One more pass required.")
                    continue
                if assessment.result is RecitationResult.RETRY:
                    _handle_reinforcement(container, active.id, active.canonical_text)
                    continue
                typer.echo("Manual review required.")
                return

            if session.phase is LearningPhase.NEEDS_REINFORCEMENT:
                _handle_reinforcement(container, active.id, active.canonical_text)
                continue

            if session.phase is LearningPhase.LEARNED:
                updated = container.psalm_learning_service.advance_after_passage_learned(
                    view.psalm.id
                )
                if _render_completed_states(updated):
                    return
                continue


def _render_completed_states(view: PsalmLearningViewDTO) -> bool:
    if view.plan.status is PsalmLearningStatus.LEARNED:
        typer.echo("Psalm learned. Use `psalter review` for due review sessions.")
        return True
    if view.plan.status is PsalmLearningStatus.CONSOLIDATING and not view.consolidation_available:
        typer.echo(f"Psalm {view.psalm.psalm_number} is only partially imported.")
        typer.echo("Whole-Psalm consolidation is unavailable.")
        return True
    return False


def _print_header(view: PsalmLearningViewDTO, passage: PassageDetailDTO) -> None:
    typer.echo("")
    typer.echo(f"Psalm {view.psalm.psalm_number}")
    typer.echo(f"Translation: {view.psalm.translation_id.upper()}")
    typer.echo(f"Status: {view.plan.status.value.replace('_', ' ')}")
    if passage.kind is PassageKind.CONSOLIDATION:
        typer.echo("Current section: complete Psalm")
    else:
        typer.echo(f"Current section: {_section_label(passage)}")
        if view.section_index is not None:
            typer.echo(f"Section {view.section_index} of {view.section_count}")
    typer.echo(f"Sections learned: {view.sections_learned} of {view.section_count}")
    if not view.consolidation_available:
        typer.echo("Whole-Psalm consolidation unavailable: partial import.")


def _run_recitation(container: Container, passage: PassageDetailDTO) -> RecitationAssessmentDTO:
    typer.echo("")
    method = typer.prompt("Recitation method [typed/spoken]", default="typed").strip().casefold()
    if method not in {"typed", "spoken"}:
        typer.secho(
            "Invalid recitation method. Choose either typed or spoken.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    try:
        if method == "typed":
            typer.echo("Type your recitation. End with a line containing only .done")
            text = _read_multiline_submission()
            return container.recitation_service.submit_text(
                RecitationSubmission(
                    passage_id=passage.id,
                    source=RecitationSource.TYPED,
                    text=text,
                )
            )

        typer.echo("Spoken recitation selected.")
        typer.echo("Press Enter to begin recording.")
        _await_enter()
        typer.echo("Recording...")
        typer.echo("Press Enter to stop.")
        return container.spoken_recitation_service.record_transcribe_and_submit(
            passage.id,
            wait_for_stop=_wait_for_enter_with_timeout,
            before_transcribe=_print_transcribing,
        )
    except (
        PersistenceConflictError,
        AudioRecorderNotConfiguredError,
        AudioRecordingFailedError,
        AudioArtifactInvalidError,
        InvalidLearningTransitionError,
        LearningSessionNotFoundError,
        PassageNotFoundError,
        TranscriberNotConfiguredError,
        WhisperExecutableNotFoundError,
        WhisperModelNotFoundError,
        WhisperProcessFailedError,
        TranscriptOutputMissingError,
        TranscriptEmptyError,
        ArtifactCleanupFailedError,
        UnsupportedAudioPlatformError,
    ) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def _section_label(passage: PassageDetailDTO) -> str:
    if passage.start_verse == passage.end_verse:
        return f"verse {passage.start_verse}"
    return f"verses {passage.start_verse}-{passage.end_verse}"


def _read_multiline_submission() -> str:
    lines: list[str] = []
    while True:
        line = typer.prompt("", prompt_suffix="")
        if line.strip() == ".done":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _await_enter() -> None:
    input()


def _wait_for_enter_with_timeout(timeout: float | None) -> bool:
    if timeout is None:
        _await_enter()
        return True
    if sys.platform.startswith("win"):
        return _wait_for_enter_windows(timeout)
    return _wait_for_enter_posix(timeout)


def _wait_for_enter_windows(timeout: float) -> bool:
    import msvcrt

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            character = msvcrt.getwch()
            if character == "\003":
                raise KeyboardInterrupt
            if character in {"\r", "\n"}:
                return True
        time.sleep(0.01)
    return False


def _wait_for_enter_posix(timeout: float) -> bool:
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return False
    return sys.stdin.readline() != ""


def _print_transcribing() -> None:
    typer.echo("Transcribing locally...")


def _print_assessment(assessment: RecitationAssessmentDTO) -> None:
    typer.echo(f"Result: {assessment.result.value}")
    typer.echo(f"Weighted accuracy: {assessment.weighted_accuracy:.3f}")
    typer.echo(f"Omissions: {assessment.omission_count}")
    typer.echo(f"Substitutions: {assessment.substitution_count}")
    typer.echo(f"Insertions: {assessment.insertion_count}")
    typer.echo(f"Longest omitted span: {assessment.longest_omitted_span}")
    typer.echo(
        f"Remaining successful recitations required: {assessment.remaining_successes_required}"
    )
    if assessment.result is not RecitationResult.RETRY:
        return
    issues_to_show = 5
    if assessment.omissions:
        typer.echo("Omitted:")
        for item in assessment.omissions[:issues_to_show]:
            typer.echo(f'- "{item}"')
    if assessment.substitutions:
        typer.echo("Substitutions:")
        for expected, received in assessment.substitutions[:issues_to_show]:
            typer.echo(f'- expected "{expected}", received "{received}"')


def _handle_reinforcement(container: Container, passage_id: str, canonical_text: str) -> None:
    selection = (
        typer.prompt(
            "Choose reinforcement action: view, resume, exit",
            default="resume",
        )
        .strip()
        .casefold()
    )
    if selection == "view":
        typer.echo("")
        typer.echo(canonical_text)
        return
    if selection == "resume":
        container.learning_service.resume_reinforcement(passage_id)
        return
    raise typer.Exit(code=0)
