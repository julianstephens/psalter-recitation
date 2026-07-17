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
        typer.echo(f"Currently learning: {summary.passages_currently_learning}")
        typer.echo(f"Learned: {summary.passages_learned}")
        typer.echo(f"Reviews due: {summary.reviews_due}")
