from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import typer

from psalter.application.errors import PassageAlreadyExistsError
from psalter.bootstrap import build_container
from psalter.config import build_config

_API_BASE_URL = "https://bible.helloao.org/api"
_PASSAGE_PATTERN = re.compile(r"^(?P<psalm>\d+):(?P<start>\d+)-(?P<end>\d+)$")

app = typer.Typer(
    help=(
        "Seed passages from bible.helloao.org.\n"
        "Example: uv run python scripts/seed_passages_from_api.py "
        "--translation BSB --passage 23:1-3 --passage 121:1-2"
    )
)


@dataclass(frozen=True, slots=True)
class PassageSpec:
    psalm_number: int
    start_verse: int
    end_verse: int


@app.command()
def seed(
    passage: Annotated[
        list[str],
        typer.Option(
            "--passage",
            help="Passage range in Psalm format, e.g. 23:1-3. Repeat for multiple passages.",
        ),
    ],
    translation: Annotated[str, typer.Option("--translation", help="API translation ID.")] = "BSB",
    book: Annotated[str, typer.Option("--book", help="Book ID (default PSA for Psalms).")] = "PSA",
    data_dir: Annotated[
        Path | None,
        typer.Option("--data-dir", help="Override local data directory used by psalter."),
    ] = None,
    fail_on_existing: Annotated[
        bool,
        typer.Option("--fail-on-existing", help="Exit non-zero when a passage already exists."),
    ] = False,
) -> None:
    specs = tuple(_parse_passage_spec(item) for item in passage)
    chapter_payloads = _fetch_required_chapters(
        translation=translation.strip(),
        book=book.strip().upper(),
        psalm_numbers=tuple(sorted({spec.psalm_number for spec in specs})),
    )

    container = build_container(build_config(data_dir=data_dir))
    container.migrator.apply_pending()

    created_count = 0
    skipped_count = 0
    for spec in specs:
        chapter = chapter_payloads[spec.psalm_number]
        canonical_text = _extract_verse_range(chapter, spec.start_verse, spec.end_verse)
        try:
            added = container.passage_service.add(
                translation_id=translation,
                psalm_number=spec.psalm_number,
                start_verse=spec.start_verse,
                end_verse=spec.end_verse,
                canonical_text=canonical_text,
            )
        except PassageAlreadyExistsError as exc:
            skipped_count += 1
            typer.secho(f"Skipped existing passage: {exc}", fg=typer.colors.YELLOW, err=True)
            if fail_on_existing:
                raise typer.Exit(code=1) from exc
            continue
        created_count += 1
        typer.echo(f"Added passage {added.id}")

    typer.echo(f"Done. Created {created_count} passage(s), skipped {skipped_count}.")


def _parse_passage_spec(raw: str) -> PassageSpec:
    match = _PASSAGE_PATTERN.fullmatch(raw.strip())
    if match is None:
        raise typer.BadParameter(
            f"Invalid --passage value '{raw}'. Expected format like 23:1-3."
        )
    psalm_number = int(match.group("psalm"))
    start_verse = int(match.group("start"))
    end_verse = int(match.group("end"))
    if end_verse < start_verse:
        raise typer.BadParameter(
            f"Invalid --passage value '{raw}'. End verse must be >= start verse."
        )
    return PassageSpec(
        psalm_number=psalm_number,
        start_verse=start_verse,
        end_verse=end_verse,
    )


def _fetch_required_chapters(
    *,
    translation: str,
    book: str,
    psalm_numbers: tuple[int, ...],
) -> dict[int, object]:
    payloads: dict[int, object] = {}
    for psalm_number in psalm_numbers:
        url = f"{_API_BASE_URL}/{translation}/{book}/{psalm_number}.json"
        try:
            with urlopen(url, timeout=20) as response:
                payloads[psalm_number] = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise typer.BadParameter(
                f"API request failed for Psalm {psalm_number} ({url}): HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise typer.BadParameter(
                f"API request failed for Psalm {psalm_number} ({url}): {exc.reason}"
            ) from exc
    return payloads


def _extract_verse_range(chapter_payload: object, start_verse: int, end_verse: int) -> str:
    if not isinstance(chapter_payload, dict):
        raise typer.BadParameter("Unexpected API payload: chapter data must be an object.")
    chapter = chapter_payload.get("chapter")
    if not isinstance(chapter, dict):
        raise typer.BadParameter("Unexpected API payload: missing chapter object.")
    content = chapter.get("content")
    if not isinstance(content, list):
        raise typer.BadParameter("Unexpected API payload: chapter.content must be a list.")

    verse_map: dict[int, str] = {}
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "verse":
            continue
        verse_number = item.get("number")
        verse_content = item.get("content")
        if not isinstance(verse_number, int) or not isinstance(verse_content, list):
            continue
        rendered = _render_verse_content(verse_content)
        if rendered:
            verse_map[verse_number] = rendered

    lines: list[str] = []
    for verse_number in range(start_verse, end_verse + 1):
        verse_text = verse_map.get(verse_number)
        if verse_text is None:
            raise typer.BadParameter(
                f"Verse {verse_number} was not returned by the API for requested range "
                f"{start_verse}-{end_verse}."
            )
        lines.append(verse_text)
    return "\n".join(lines).strip()


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
