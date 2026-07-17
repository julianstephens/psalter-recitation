# psalter-recitation

A CLI-first application for Psalm memorization and review.

## Purpose

This project models and orchestrates a learning flow:

1. Exposure: show the complete canonical passage.
2. Practice: progress through deterministic masking levels.
3. Typed recitation: submit unaided text (`.done` ends multiline input).
4. Assessment: normalize and align text with weighted scoring.
5. Confirmation: require two passing unaided recitations before learned.
6. Scheduling: create initial review one day after learning.

The CLI and any future UI must share the same application services and domain model.

## Status

Implemented:

- Ports-and-adapters structure with inward dependency direction.
- Typed domain models and state transitions.
- Application services for passage management, learning workflow, typed recitation assessment, review lookup, and progress.
- SQLite adapter with tracked SQL migrations.
- Typer commands: init, passage add/list/show, learn, review, progress.
- Unit and integration tests.

Currently unsupported / intentionally deferred:

- Audio recording.
- Speech recognition transcription.
- Pronunciation scoring.
- Semantic paraphrase acceptance.
- Full seven-station review schedule.
- Final assessment thresholds (provisional and versioned).

## Setup

```bash
uv sync
uv run psalter init
uv run psalter passage add --translation-id esv --psalm 23 --start-verse 1 --end-verse 1 --text "The LORD is my shepherd."
uv run psalter passage list
uv run psalter passage show esv-psalm-23-1-1
uv run psalter learn esv-psalm-23-1-1
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

When `psalter learn` reaches recitation, enter multiple lines and terminate input with a line containing only `.done`.

Assessment currently performs textual normalization/alignment only. It does not evaluate pronunciation and does not accept semantic paraphrase substitutions.

## Project Structure

```text
src/psalter/
	cli/             # CLI adapter only (parsing + presentation)
	application/     # services, DTOs, app-level errors
	domain/          # entities, value constraints, transition rules
	ports/           # dependency-inversion protocols
	adapters/        # sqlite/system/unsupported implementations
	bootstrap.py     # composition root
	config.py        # local path configuration
```