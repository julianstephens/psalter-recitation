from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.bootstrap import build_container
from psalter.cli.readiness import require_ready
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    @app.command("review")
    def review_command(
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        require_ready(container)
        due = container.review_service.get_due_psalm_reviews()
        if not due:
            typer.echo("No reviews due.")
            return

        for item in due:
            typer.echo(f"Psalm {item.psalm_number}")
            typer.echo(f"Translation: {item.translation_id}")
            typer.echo(f"Due: {item.due_label}")
            typer.echo(f"Reason: {item.reason}")
            if item.next_review_at is not None:
                typer.echo(f"Next review at: {item.next_review_at}")
            typer.echo("")
