from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from psalter.application.errors import (
    InvalidPassageError,
    PsalmAlreadyExistsError,
    PsalmNotFoundError,
    PsalmTranslationAmbiguousError,
)
from psalter.bootstrap import build_container
from psalter.cli.readiness import require_ready
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    psalm_app = typer.Typer(help="Manage Psalms and their generated internal sections.")

    @psalm_app.command("add")
    def add_command(
        psalm_number: Annotated[int, typer.Argument(help="Psalm number.")],
        translation_id: Annotated[str, typer.Option("--translation-id")] = "BSB",
        verse: Annotated[
            list[str] | None,
            typer.Option(
                "--verse",
                help="Repeat NUMBER:TEXT for each verse, e.g. --verse 1:Blessed is the man.",
            ),
        ] = None,
        json_file: Annotated[
            Path | None,
            typer.Option("--json-file", help="JSON file with ordered verse records."),
        ] = None,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()

        try:
            verses = _resolve_verses(verse=tuple(verse or ()), json_file=json_file)
            added = container.psalm_service.add(
                translation_id=translation_id,
                psalm_number=psalm_number,
                verses=verses,
            )
        except (InvalidPassageError, PsalmAlreadyExistsError, typer.BadParameter) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(f"Added Psalm {added.psalm_number} ({added.translation_id})")
        typer.echo(f"Verses: {added.verse_count}")

    @psalm_app.command("list")
    def list_command(
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        require_ready(container)
        psalms = container.psalm_service.list_all()
        if not psalms:
            typer.echo("No Psalms imported.")
            return
        for psalm in psalms:
            typer.echo(
                f"Psalm {psalm.psalm_number} ({psalm.translation_id}) "
                f"- {psalm.completeness.value}, {psalm.verse_count} verses"
            )

    @psalm_app.command("show")
    def show_command(
        psalm_number: Annotated[int, typer.Argument(help="Psalm number.")],
        translation_id: Annotated[str | None, typer.Option("--translation-id")] = None,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        require_ready(container)
        try:
            progress = container.psalm_learning_service.get_progress(
                psalm_number=psalm_number,
                translation_id=translation_id,
            )
            psalm = container.psalm_service.get_by_translation_and_number(
                translation_id=progress.translation_id,
                psalm_number=psalm_number,
            )
            if psalm is None:
                raise PsalmNotFoundError(f"Psalm {psalm_number} was not found.")
        except (PsalmNotFoundError, PsalmTranslationAmbiguousError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(f"Psalm {psalm.psalm_number}")
        typer.echo(f"Translation: {psalm.translation_id}")
        typer.echo(f"Completeness: {psalm.completeness.value}")
        typer.echo("")
        if psalm.verses:
            for verse in psalm.verses:
                typer.echo(f"{verse.verse_number}. {verse.canonical_text}")
            return
        typer.echo(psalm.canonical_text)

    app.add_typer(psalm_app, name="psalm")


def _resolve_verses(
    *,
    verse: tuple[str, ...],
    json_file: Path | None,
) -> tuple[tuple[int, str], ...]:
    if json_file is not None:
        return _load_json_verses(json_file)
    if verse:
        return tuple(_parse_verse_option(item) for item in verse)
    return _prompt_verses()


def _load_json_verses(json_file: Path) -> tuple[tuple[int, str], ...]:
    raw = json.loads(json_file.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise typer.BadParameter("Verse JSON must be an array.")
    verses: list[tuple[int, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise typer.BadParameter("Each verse record must be an object.")
        verse_number = item.get("verse_number", item.get("number"))
        canonical_text = item.get("canonical_text", item.get("text"))
        if not isinstance(verse_number, int) or not isinstance(canonical_text, str):
            raise typer.BadParameter("Verse records must include integer number and string text.")
        verses.append((verse_number, canonical_text))
    return tuple(verses)


def _parse_verse_option(raw: str) -> tuple[int, str]:
    number_text, separator, verse_text = raw.partition(":")
    if separator != ":":
        raise typer.BadParameter(f"Invalid --verse value '{raw}'. Use NUMBER:TEXT.")
    try:
        verse_number = int(number_text)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid verse number in '{raw}'.") from exc
    return verse_number, verse_text


def _prompt_verses() -> tuple[tuple[int, str], ...]:
    typer.echo("Enter verses one at a time. Leave the verse number blank when finished.")
    verses: list[tuple[int, str]] = []
    while True:
        raw_number = typer.prompt("Verse number", default="", show_default=False).strip()
        if not raw_number:
            break
        verse_number = int(raw_number)
        verse_text = typer.prompt("Verse text").strip()
        verses.append((verse_number, verse_text))
    if not verses:
        raise typer.BadParameter("At least one verse is required.")
    return tuple(verses)
