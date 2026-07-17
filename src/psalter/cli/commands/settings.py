from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.bootstrap import build_container
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    @app.command("settings")
    def settings_command(
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        settings = container.installer.get_settings()
        if settings is None:
            typer.echo("Installation settings not found.")
            return
        installed = container.installer.list_installed_translations()
        typer.echo(f"Catalog status: {settings.catalog_status.value}")
        typer.echo(f"Scripture provider: {settings.scripture_provider}")
        if settings.default_translation_id is not None:
            typer.echo(f"Default translation: {settings.default_translation_id}")
        if installed:
            typer.echo("Installed translations:")
            for item in installed:
                suffix = (
                    " (default)" if item.translation_id == settings.default_translation_id else ""
                )
                typer.echo(f"  {item.translation_id} - {item.psalm_count} Psalms{suffix}")
        if settings.initialized_at is not None:
            typer.echo(f"Initialized at: {settings.initialized_at.isoformat()}")
        if settings.last_error:
            typer.echo(f"Last error: {settings.last_error}")
