from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.bootstrap import build_container
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
        due = container.review_service.get_due_reviews()
        if not due:
            typer.echo("No reviews due.")
            return

        for item in due:
            typer.echo(
                f"Passage {item.passage_id} due at {item.next_review_at} (station {item.station})"
            )
