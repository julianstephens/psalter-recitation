from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from psalter.application.errors import (
    InvalidPassageError,
    PassageAlreadyExistsError,
    PassageNotFoundError,
    PsalmAlreadyExistsError,
)
from psalter.bootstrap import build_container
from psalter.config import build_config


def register(app: typer.Typer) -> None:
    passage_app = typer.Typer(help="Manage passages.")

    @passage_app.command("add")
    def add_command(
        translation_id: Annotated[str | None, typer.Option("--translation-id")] = None,
        psalm: Annotated[int | None, typer.Option("--psalm")] = None,
        start_verse: Annotated[int | None, typer.Option("--start-verse")] = None,
        end_verse: Annotated[int | None, typer.Option("--end-verse")] = None,
        text: Annotated[str | None, typer.Option("--text")] = None,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()

        resolved_translation_id = translation_id or typer.prompt("Translation ID").strip()
        resolved_psalm = psalm or int(typer.prompt("Psalm number"))
        resolved_start = start_verse or int(typer.prompt("Start verse"))
        resolved_end = end_verse or int(typer.prompt("End verse"))
        resolved_text = text or _prompt_multiline_text()

        try:
            added = container.passage_service.add(
                translation_id=resolved_translation_id,
                psalm_number=resolved_psalm,
                start_verse=resolved_start,
                end_verse=resolved_end,
                canonical_text=resolved_text,
            )
        except (PassageAlreadyExistsError, InvalidPassageError, PsalmAlreadyExistsError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(f"Added passage {added.id}")
        typer.echo(
            "Note: passage add creates or extends a partial Psalm import. "
            "Upgrading that Psalm to a complete Psalm import is not supported yet."
        )

    @passage_app.command("list")
    def list_command(
        psalm: Annotated[int | None, typer.Option("--psalm")] = None,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        passages = container.passage_service.list_all()
        if psalm is not None:
            passages = [item for item in passages if item.psalm_number == psalm]
        if not passages:
            typer.echo("No passages configured.")
            return
        for passage in passages:
            if passage.kind.value == "consolidation":
                typer.echo(
                    f"{passage.id} ({passage.translation_id} Psalm "
                    f"{passage.psalm_number}, consolidation)"
                )
                continue
            typer.echo(
                f"{passage.id} ({passage.translation_id} Psalm "
                f"{passage.psalm_number}:{passage.start_verse}-{passage.end_verse}, "
                f"section {passage.sequence_number})"
            )

    @passage_app.command("show")
    def show_command(
        passage_id: str,
        data_dir: Annotated[
            Path | None,
            typer.Option(help="Override local data directory"),
        ] = None,
    ) -> None:
        container = build_container(build_config(data_dir=data_dir))
        container.migrator.apply_pending()
        try:
            passage = container.passage_service.get_by_id(passage_id)
        except PassageNotFoundError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        label = (
            f"{passage.translation_id} Psalm {passage.psalm_number}"
            if passage.kind.value == "consolidation"
            else (
                f"{passage.translation_id} Psalm {passage.psalm_number}:"
                f"{passage.start_verse}-{passage.end_verse}"
            )
        )
        typer.echo(f"{passage.id} ({label})")
        typer.echo("")
        typer.echo(passage.canonical_text)

    app.add_typer(passage_app, name="passage")


def _prompt_multiline_text() -> str:
    typer.echo("Enter canonical text. Finish with a line containing only .done")
    lines: list[str] = []
    while True:
        line = typer.prompt("", prompt_suffix="")
        if line.strip() == ".done":
            break
        lines.append(line)
    return "\n".join(lines).strip()
