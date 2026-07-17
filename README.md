# psalter-recitation

A CLI-first application scaffold for Psalm memorization and review.

## Purpose

This project models and orchestrates a Psalm learning flow:

1. Exposure: show the complete passage.
2. Practice: progress through reduced text prompts.
3. Proof: record an unaided spoken recitation.
4. Assessment: transcribe and compare with canonical text.
5. Scheduling: mark learned only after passing assessment, then schedule reviews.

The CLI and any future UI must share the same application services and domain model.

## Status

Implemented in this scaffold:

- Ports-and-adapters structure with inward dependency direction.
- Typed domain models and state transitions.
- Application services for learning, recitation orchestration shape, review lookup, and progress.
- SQLite adapter with tracked SQL migrations.
- Typer commands: init, learn, review, progress.
- Unit and integration tests.

Deliberately not implemented yet:

- Audio recording provider.
- Transcription provider.
- Transcript assessment policy.
- Full practice interaction algorithm.
- Full review station scheduling algorithm.

## Setup

```bash
uv sync
uv run psalter init
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

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