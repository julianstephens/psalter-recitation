from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.application.errors import NotFoundError
from psalter.bootstrap import build_container
from psalter.config import build_config


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
            session = container.learning_service.begin_or_resume(passage_id)
            passage = container.learning_service.get_passage(passage_id)
        except NotFoundError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(
            " ".join(
                [
                    f"Passage {passage_id}",
                    f"(Psalm {passage.psalm_number}:{passage.start_verse}-{passage.end_verse})",
                    f"phase={session.phase.value}",
                ]
            )
        )
