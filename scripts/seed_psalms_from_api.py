from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.application.errors import ApplicationError
from psalter.bootstrap import build_container
from psalter.config import build_config

app = typer.Typer(
    help=(
        "Development wrapper around the catalog installer.\n"
        "This script intentionally delegates to the same installer used by `psalter init`."
    )
)


@app.command()
def seed(
    translation: Annotated[str, typer.Option("--translation")] = "BSB",
    resume: Annotated[bool, typer.Option("--resume")] = False,
    repair: Annotated[bool, typer.Option("--repair")] = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    container = build_container(build_config(data_dir=data_dir))
    container.migrator.apply_pending()
    try:
        result = container.installer.initialize(translation, resume=resume, repair=repair)
    except ApplicationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Installed translation {result.translation_id}: "
        f"imported {result.imported_psalm_count}, skipped {result.skipped_psalm_count}."
    )


if __name__ == "__main__":
    app()
