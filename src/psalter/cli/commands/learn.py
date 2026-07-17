from __future__ import annotations

import select
import sys
import time
from pathlib import Path
from typing import Annotated

import typer

from psalter.application.dto import (
    PassageDetailDTO,
    PracticeKind,
    PsalmLearningScreen,
    PsalmLearningScreenDTO,
    PsalmLearningViewDTO,
    RecitationAssessmentDTO,
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
    StaleLearningTargetError,
    TranscriberNotConfiguredError,
    TranscriptEmptyError,
    TranscriptOutputMissingError,
    UnsupportedAudioPlatformError,
    WhisperExecutableNotFoundError,
    WhisperModelNotFoundError,
    WhisperProcessFailedError,
)
from psalter.application.services.workflow import PsalmLearningWorkflow
from psalter.bootstrap import build_container
from psalter.cli.readiness import require_ready
from psalter.config import build_config
from psalter.domain.passage import PassageKind
from psalter.domain.recitation import RecitationResult


def register(app: typer.Typer) -> None:
    @app.command("learn")
    def learn_command(
        psalm_number: int,
        translation_id: Annotated[str | None, typer.Option("--translation-id")] = None,
        data_dir: Annotated[Path | None, typer.Option(help="Override local data directory")] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        require_ready(container)
        workflow = PsalmLearningWorkflow(
            psalm_learning_service=container.psalm_learning_service,
            learning_service=container.learning_service,
            recitation_service=container.recitation_service,
            spoken_recitation_service=container.spoken_recitation_service,
        )
        try:
            state = workflow.start_or_resume(psalm_number=psalm_number, translation_id=translation_id)
        except (PsalmNotFoundError, PsalmTranslationAmbiguousError, NoActivePassageError, PsalmLearningPlanConflictError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        while True:
            if _render_completed_states(state):
                return
            active = state.view.active_passage
            if active is None:
                typer.secho("No active passage is available.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            _print_header(state.view, active)

            if state.screen is PsalmLearningScreen.EXPOSURE:
                typer.echo("")
                typer.echo(active.canonical_text)
                prompt = "Read the complete Psalm, then continue to recitation?" if active.kind is PassageKind.CONSOLIDATION else "Read attentively, then continue to practice?"
                if not typer.confirm("\n\n" + prompt, default=True):
                    return
                state = workflow.complete_exposure(
                    psalm_number=psalm_number,
                    translation_id=translation_id,
                    target_token=state.active_target.token if state.active_target else None,
                )
                continue

            if state.screen is PsalmLearningScreen.PRACTICE:
                practice = state.practice
                if practice is None:
                    typer.secho("Practice view was not available.", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1)
                typer.echo("")
                if practice.kind is PracticeKind.SHADOW_TYPING:
                    typer.echo("Shadow typing")
                    typer.echo("Copy the passage while looking at it. End with a line containing only .done.")
                    typer.echo("")
                    typer.echo(practice.canonical_text or active.canonical_text)
                    typer.echo("")
                    typer.echo("Your copy:")
                    result = container.learning_service.submit_shadow_typing(
                        active.id,
                        _read_multiline_submission(),
                    )
                    if result.accepted:
                        typer.echo("Shadow typing complete. Beginning masked recall.")
                        state = workflow.start_or_resume(psalm_number=psalm_number, translation_id=translation_id)
                    else:
                        typer.secho("Your copy does not yet match the passage.", fg=typer.colors.YELLOW)
                        if result.mismatch_excerpt:
                            typer.echo(f'Check near: "{result.mismatch_excerpt}"')
                        if not typer.confirm("Try again?", default=True):
                            return
                    continue
                typer.echo(practice.masked_text or "")
                if not typer.confirm(f"Complete practice level {practice.level}?", default=True):
                    return
                state = workflow.complete_practice(
                    psalm_number=psalm_number,
                    translation_id=translation_id,
                    target_token=state.active_target.token if state.active_target else None,
                )
                continue

            if state.screen is PsalmLearningScreen.READY_FOR_RECITATION:
                state = _run_recitation(workflow, state, psalm_number, translation_id)
                assessment = state.assessment
                if assessment is None:
                    typer.secho("Recitation assessment was not available.", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1)
                _print_assessment(assessment)
                if state.screen is PsalmLearningScreen.PSALM_COMPLETED:
                    typer.echo("Whole Psalm learned. Use `psalter review` for due reviews.")
                    return
                if state.screen is PsalmLearningScreen.CONSOLIDATION_UNAVAILABLE:
                    typer.echo(f"Psalm {psalm_number} is only partially imported.")
                    typer.echo("Whole-Psalm consolidation is unavailable.")
                    return
                if state.screen is PsalmLearningScreen.CONSOLIDATION_STARTED:
                    typer.echo("All sections learned. Entering whole-Psalm consolidation.")
                    state = workflow.start_or_resume(psalm_number=psalm_number, translation_id=translation_id)
                    continue
                if state.screen is PsalmLearningScreen.SECTION_COMPLETED:
                    typer.echo("Section learned.")
                    state = workflow.start_or_resume(psalm_number=psalm_number, translation_id=translation_id)
                    if state.view.active_passage is not None:
                        typer.echo(f"Advancing to {_section_label(state.view.active_passage)}.")
                    continue
                if assessment.result is RecitationResult.PASS:
                    typer.echo("Successful recitation recorded. One more pass required.")
                    continue
                if state.screen is PsalmLearningScreen.REINFORCEMENT:
                    state = _handle_reinforcement(workflow, state, psalm_number, translation_id, active)
                    continue
                typer.echo("Manual review required.")
                return

            if state.screen is PsalmLearningScreen.REINFORCEMENT:
                state = _handle_reinforcement(workflow, state, psalm_number, translation_id, active)
                continue
            typer.echo("Manual review required.")
            return


def _render_completed_states(state: PsalmLearningScreenDTO) -> bool:
    if state.screen is PsalmLearningScreen.PSALM_COMPLETED:
        typer.echo("Psalm learned. Use `psalter review` for due review sessions.")
        return True
    if state.screen is PsalmLearningScreen.CONSOLIDATION_UNAVAILABLE:
        typer.echo(f"Psalm {state.view.psalm.psalm_number} is only partially imported.")
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


def _run_recitation(workflow: PsalmLearningWorkflow, state: PsalmLearningScreenDTO, psalm_number: int, translation_id: str | None) -> PsalmLearningScreenDTO:
    passage = state.view.active_passage
    if passage is None:
        typer.secho("No active passage is available.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    method = typer.prompt("Recitation method [typed/spoken]", default="typed").strip().casefold()
    if method not in {"typed", "spoken"}:
        raise typer.Exit(code=1)
    try:
        if method == "typed":
            typer.echo("Type your recitation. End with a line containing only .done")
            return workflow.submit_typed_recitation(
                psalm_number=psalm_number,
                translation_id=translation_id,
                text=_read_multiline_submission(),
                target_token=state.active_target.token if state.active_target else None,
            )
        typer.echo("Press Enter to begin recording.")
        _await_enter()
        typer.echo("Recording... Press Enter to stop.")
        return workflow.submit_recorded_recitation(
            psalm_number=psalm_number,
            translation_id=translation_id,
            target_token=state.active_target.token if state.active_target else None,
            wait_for_stop=_wait_for_enter_with_timeout,
            before_transcribe=_print_transcribing,
        )
    except (PersistenceConflictError, AudioRecorderNotConfiguredError, AudioRecordingFailedError, AudioArtifactInvalidError, InvalidLearningTransitionError, LearningSessionNotFoundError, PassageNotFoundError, TranscriberNotConfiguredError, WhisperExecutableNotFoundError, WhisperModelNotFoundError, WhisperProcessFailedError, TranscriptOutputMissingError, TranscriptEmptyError, ArtifactCleanupFailedError, UnsupportedAudioPlatformError, StaleLearningTargetError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def _section_label(passage: PassageDetailDTO) -> str:
    return f"verse {passage.start_verse}" if passage.start_verse == passage.end_verse else f"verses {passage.start_verse}-{passage.end_verse}"


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
    return bool(ready and sys.stdin.readline() != "")


def _print_transcribing() -> None:
    typer.echo("Transcribing locally...")


def _print_assessment(assessment: RecitationAssessmentDTO) -> None:
    typer.echo(f"Result: {assessment.result.value}")
    typer.echo(f"Weighted accuracy: {assessment.weighted_accuracy:.3f}")
    typer.echo(f"Omissions: {assessment.omission_count}")
    typer.echo(f"Substitutions: {assessment.substitution_count}")
    typer.echo(f"Insertions: {assessment.insertion_count}")
    typer.echo(f"Longest omitted span: {assessment.longest_omitted_span}")
    typer.echo(f"Remaining successful recitations required: {assessment.remaining_successes_required}")


def _handle_reinforcement(workflow: PsalmLearningWorkflow, state: PsalmLearningScreenDTO, psalm_number: int, translation_id: str | None, passage: PassageDetailDTO) -> PsalmLearningScreenDTO:
    selection = typer.prompt("Choose reinforcement action: view, resume, exit", default="resume").strip().casefold()
    if selection == "view":
        typer.echo(passage.canonical_text)
        return state
    if selection == "resume":
        return workflow.resume_reinforcement(
            psalm_number=psalm_number,
            translation_id=translation_id,
            target_token=state.active_target.token if state.active_target else None,
        )
    raise typer.Exit(code=0)
