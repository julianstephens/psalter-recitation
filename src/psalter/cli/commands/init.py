from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.bootstrap import initialize_storage
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_command(
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        config = initialize_storage(build_config(data_dir=data_dir))
        typer.echo(f"Database ready at {config.db_path}")
