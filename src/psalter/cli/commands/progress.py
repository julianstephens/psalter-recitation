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
