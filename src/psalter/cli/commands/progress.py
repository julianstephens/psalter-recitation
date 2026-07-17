from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.bootstrap import build_container
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    @app.command("progress")
    def progress_command(
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        summary = container.progress_service.summary()
        due_by_psalm: dict[str, int] = {}
        for item in container.review_service.get_due_psalm_reviews():
            due_by_psalm[item.psalm_id] = due_by_psalm.get(item.psalm_id, 0) + 1
        psalms = container.psalm_learning_service.list_progress()
        typer.echo(f"Total passages: {summary.total_passages}")
        typer.echo(f"Unseen passages: {summary.unseen_passages}")
        typer.echo(f"Exposure passages: {summary.exposure_passages}")
        typer.echo(f"Practice passages: {summary.practice_passages}")
        typer.echo(f"Ready passages: {summary.ready_passages}")
        typer.echo(f"Reinforcement passages: {summary.reinforcement_passages}")
        typer.echo(f"Learned passages: {summary.learned_passages}")
        typer.echo(f"Reviews due: {summary.reviews_due}")
        typer.echo(f"Total recitation attempts: {summary.total_recitation_attempts}")
        typer.echo(f"Successful recitation attempts: {summary.successful_recitation_attempts}")
        if not psalms:
            return
        for psalm in psalms:
            typer.echo("")
            typer.echo(f"Psalm {psalm.psalm_number} - {psalm.translation_id}")
            typer.echo(f"Status: {psalm.status.value.replace('_', ' ')}")
            typer.echo(f"Sections learned: {psalm.sections_learned}/{psalm.section_count}")
            if psalm.current_section_label is not None:
                typer.echo(f"Current section: {psalm.current_section_label}")
            typer.echo(f"Reviews due: {due_by_psalm.get(psalm.psalm_id, 0)}")
            if not psalm.consolidation_available:
                typer.echo("Whole-Psalm consolidation unavailable: partial import.")
