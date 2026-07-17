from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import typer

from psalter.application.errors import PsalmAlreadyExistsError
from psalter.bootstrap import build_container
from psalter.config import build_config

_API_BASE_URL = "https://bible.helloao.org/api"

app = typer.Typer(
    help=(
        "Seed complete Psalms from bible.helloao.org.\n"
        "Example: uv run python scripts/seed_psalms_from_api.py "
        "--translation BSB --psalm 23 --psalm 90"
    )
)


@dataclass(frozen=True, slots=True)
class VerseRecord:
    verse_number: int
    canonical_text: str


@app.command()
def seed(
    psalm: Annotated[
        list[int],
        typer.Option(
            "--psalm",
            help="Psalm number to import. Repeat for multiple Psalms.",
        ),
    ],
    translation: Annotated[
        str,
        typer.Option("--translation", help="API translation ID."),
    ] = "BSB",
    book: Annotated[
        str,
        typer.Option("--book", help="Book ID (default PSA for Psalms)."),
    ] = "PSA",
    data_dir: Annotated[
        Path | None,
        typer.Option("--data-dir", help="Override local data directory used by psalter."),
    ] = None,
) -> None:
    container = build_container(build_config(data_dir=data_dir))
    container.migrator.apply_pending()

    created_count = 0
    skipped_count = 0
    for psalm_number in psalm:
        verses = _fetch_psalm(
            translation=translation.strip(),
            book=book.strip().upper(),
            psalm_number=psalm_number,
        )
        try:
            container.psalm_service.add(
                translation_id=translation,
                psalm_number=psalm_number,
                verses=tuple((verse.verse_number, verse.canonical_text) for verse in verses),
            )
        except PsalmAlreadyExistsError as exc:
            skipped_count += 1
            typer.secho(f"Skipped existing Psalm: {exc}", fg=typer.colors.YELLOW, err=True)
            continue
        created_count += 1
        passages = [
            passage
            for passage in container.passage_service.list_all()
            if passage.translation_id == translation
            and passage.psalm_number == psalm_number
            and passage.kind.value == "section"
        ]
        ranges = ", ".join(f"{item.start_verse}-{item.end_verse}" for item in passages)
        typer.echo(f"Added Psalm {psalm_number} ({translation})")
        typer.echo(f"Generated sections: {ranges}")

    typer.echo(f"Done. Created {created_count} Psalm(s), skipped {skipped_count}.")


def _fetch_psalm(*, translation: str, book: str, psalm_number: int) -> tuple[VerseRecord, ...]:
    url = f"{_API_BASE_URL}/{translation}/{book}/{psalm_number}.json"
    try:
        with urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise typer.BadParameter(
            f"API request failed for Psalm {psalm_number} ({url}): HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise typer.BadParameter(
            f"API request failed for Psalm {psalm_number} ({url}): {exc.reason}"
        ) from exc
    return _extract_verses(payload)


def _extract_verses(chapter_payload: object) -> tuple[VerseRecord, ...]:
    if not isinstance(chapter_payload, dict):
        raise typer.BadParameter("Unexpected API payload: chapter data must be an object.")
    chapter = chapter_payload.get("chapter")
    if not isinstance(chapter, dict):
        raise typer.BadParameter("Unexpected API payload: missing chapter object.")
    content = chapter.get("content")
    if not isinstance(content, list):
        raise typer.BadParameter("Unexpected API payload: chapter.content must be a list.")

    verses: list[VerseRecord] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "verse":
            continue
        verse_number = item.get("number")
        verse_content = item.get("content")
        if not isinstance(verse_number, int) or not isinstance(verse_content, list):
            raise typer.BadParameter("Unexpected API payload: malformed verse record.")
        rendered = _render_verse_content(verse_content)
        if not rendered:
            raise typer.BadParameter(
                f"Unexpected API payload: Psalm verse {verse_number} is blank."
            )
        verses.append(VerseRecord(verse_number=verse_number, canonical_text=rendered))

    if not verses:
        raise typer.BadParameter("Unexpected API payload: no verses were returned.")
    expected_numbers = list(range(1, len(verses) + 1))
    actual_numbers = [item.verse_number for item in verses]
    if actual_numbers != expected_numbers:
        raise typer.BadParameter("Unexpected API payload: verses must be complete and contiguous.")
    return tuple(verses)


def _render_verse_content(chunks: list[object]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, str):
            parts.append(chunk)
            continue
        if not isinstance(chunk, dict):
            continue
        text = chunk.get("text")
        if isinstance(text, str):
            parts.append(text)
            continue
        heading = chunk.get("heading")
        if isinstance(heading, str):
            parts.append(heading)
            continue
        if chunk.get("lineBreak") is True:
            parts.append("\n")
    return _normalize_rendered_text("".join(parts))


def _normalize_rendered_text(text: str) -> str:
    compact_lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in compact_lines if line).strip()


if __name__ == "__main__":
    app()
