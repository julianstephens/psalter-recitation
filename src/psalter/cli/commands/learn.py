from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.application.dto import RecitationAssessmentDTO, RecitationSubmission
from psalter.application.errors import (
    InvalidLearningTransitionError,
    LearningSessionNotFoundError,
    PassageNotFoundError,
)
from psalter.bootstrap import Container, build_container
from psalter.config import build_config
from psalter.domain.learning import LearningPhase
from psalter.domain.recitation import RecitationResult, RecitationSource


def register(app: typer.Typer) -> None:
    @app.command("learn")
    def learn_command(
        passage_id: str,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        try:
            container.learning_service.begin_or_resume(passage_id)
        except PassageNotFoundError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        while True:
            try:
                view = container.learning_service.get_learning_view(passage_id)
            except (PassageNotFoundError, LearningSessionNotFoundError) as exc:
                typer.secho(str(exc), fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1) from exc

            session = view.session
            passage = view.passage
            typer.echo("")
            typer.echo(
                f"{passage.translation_id} Psalm {passage.psalm_number}:"
                f"{passage.start_verse}-{passage.end_verse}"
            )
            typer.echo(f"Phase: {session.phase.value}")

            if session.phase is LearningPhase.EXPOSURE:
                typer.echo("")
                typer.echo(passage.canonical_text)
                if not typer.confirm("Read attentively, then continue to practice?", default=True):
                    return
                try:
                    container.learning_service.complete_exposure(passage_id)
                except InvalidLearningTransitionError as exc:
                    typer.secho(str(exc), fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1) from exc
                continue

            if session.phase is LearningPhase.PRACTICE:
                practice = container.learning_service.get_practice_view(passage_id)
                typer.echo("")
                typer.echo(practice.masked_text)
                if not typer.confirm(
                    f"Complete practice level {practice.level}?",
                    default=True,
                ):
                    return
                try:
                    container.learning_service.complete_practice_level(passage_id)
                except InvalidLearningTransitionError as exc:
                    typer.secho(str(exc), fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1) from exc
                continue

            if session.phase is LearningPhase.READY_FOR_RECITATION:
                typer.echo("")
                typer.echo("Type your recitation. End with a line containing only .done")
                text = _read_multiline_submission()
                assessment = container.recitation_service.submit_text(
                    RecitationSubmission(
                        passage_id=passage_id,
                        source=RecitationSource.TYPED,
                        text=text,
                    )
                )
                _print_assessment(assessment)
                if (
                    assessment.result is RecitationResult.PASS
                    and assessment.remaining_successes_required == 0
                ):
                    typer.echo("Passage learned. Initial review scheduled for one day from now.")
                    return
                if assessment.result is RecitationResult.PASS:
                    typer.echo("First successful recitation recorded. One more pass required.")
                    continue
                if assessment.result is RecitationResult.RETRY:
                    _handle_reinforcement(container, passage_id, passage.canonical_text)
                    continue
                typer.echo("Manual review required.")
                return

            if session.phase is LearningPhase.NEEDS_REINFORCEMENT:
                _handle_reinforcement(container, passage_id, passage.canonical_text)
                continue

            if session.phase is LearningPhase.LEARNED:
                typer.echo("Already learned. Use `psalter review` for due review sessions.")
                return


def _read_multiline_submission() -> str:
    lines: list[str] = []
    while True:
        line = typer.prompt("", prompt_suffix="")
        if line.strip() == ".done":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _print_assessment(assessment: RecitationAssessmentDTO) -> None:
    # DTO shape stays presentation-neutral; CLI rendering is intentionally local.
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
        if len(assessment.omissions) > issues_to_show:
            typer.echo(
                f"... and {len(assessment.omissions) - issues_to_show} more omission issue(s)"
            )
    if assessment.substitutions:
        typer.echo("Substitutions:")
        for expected, received in assessment.substitutions[:issues_to_show]:
            typer.echo(f'- expected "{expected}", received "{received}"')
        if len(assessment.substitutions) > issues_to_show:
            typer.echo(
                "... and "
                f"{len(assessment.substitutions) - issues_to_show} more substitution issue(s)"
            )


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
