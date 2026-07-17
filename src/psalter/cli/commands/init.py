from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.application.errors import (
    ApplicationError,
    TranslationNotSupportedError,
)
from psalter.bootstrap import build_container
from psalter.config import build_config
from psalter.ports.scripture_catalog_provider import TranslationInfo


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_command(
        translation: Annotated[str | None, typer.Option("--translation")] = None,
        resume: Annotated[bool, typer.Option("--resume")] = False,
        repair: Annotated[bool, typer.Option("--repair")] = False,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        settings = container.installer.get_settings()
        if (
            settings is not None
            and settings.catalog_status.value == "ready"
            and not any([translation, resume, repair])
        ):
            typer.echo(f"Psalter is already initialized with {settings.default_translation_id}.")
            return
        selected_translation = translation or _prompt_translation(
            container.installer.list_translations()
        )
        typer.echo(f"Installing {selected_translation.upper()} Psalter...")
        try:
            result = container.installer.initialize(
                selected_translation,
                resume=resume,
                repair=repair,
            )
        except (ApplicationError, ValueError, TypeError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(f"Imported {result.imported_psalm_count} Psalms.")
        if result.skipped_psalm_count:
            typer.echo(f"Skipped {result.skipped_psalm_count} already valid Psalms.")
        typer.echo("Generated learning sections.")
        typer.echo(f"Default translation: {result.translation_id}.")
        typer.echo("")
        typer.echo("Psalter is ready.")
        typer.echo("")
        typer.echo("Begin with:")
        typer.echo("  psalter learn 90")


def _prompt_translation(translations: tuple[TranslationInfo, ...]) -> str:
    if not translations:
        raise TranslationNotSupportedError("No supported translations are available.")
    typer.echo("Choose a translation:")
    typer.echo("")
    for index, item in enumerate(translations, start=1):
        translation_id = item.id
        name = item.name
        typer.echo(f"{index}. {translation_id} -- {name}")
    typer.echo("")
    raw = typer.prompt("Selection").strip()
    if raw.isdigit():
        selected_index = int(raw)
        if 1 <= selected_index <= len(translations):
            return translations[selected_index - 1].id
    for item in translations:
        translation_id = item.id
        if raw.casefold() == translation_id.casefold():
            return translation_id
    raise TranslationNotSupportedError(f"Unsupported translation: {raw}")
