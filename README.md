# psalter-recitation

A CLI-first application for Psalm memorization and review.

## Purpose

This project models and orchestrates a Psalm-first learning flow:

1. Select a Psalm by number.
2. Let the application choose and remember internal section passages.
3. Exposure: show the complete canonical section or whole Psalm target.
4. Practice: progress through deterministic masking levels for section learning.
5. Typed recitation: submit unaided text (`.done` ends multiline input).
6. Spoken recitation: record local microphone audio, transcribe with local whisper.cpp.
7. Assessment: normalize and align text with weighted scoring.
8. Confirmation: require two passing unaided recitations before a section is learned.
9. Consolidation: require two passing whole-Psalm recitations after all sections are learned.
10. Scheduling: create initial review one day after learning.

The CLI and any future UI must share the same application services and domain model.

## Status

Implemented:

- Ports-and-adapters structure with inward dependency direction.
- Typed domain models and state transitions for Psalms, passages, and learning plans.
- Application services for Psalm import, Psalm-first learning workflow, typed recitation assessment, review lookup, and progress.
- Spoken recitation orchestration that records audio and submits whisper transcript through the same recitation service path.
- SQLite adapter with tracked SQL migrations.
- Typer commands: init, psalm add/list/show, passage list/show, learn, review, progress.
- Unit and integration tests.

Currently unsupported / intentionally deferred:

- Pronunciation scoring.
- Semantic paraphrase acceptance.
- Full seven-station review schedule.
- Final assessment thresholds (provisional and versioned).

## Setup

```bash
uv sync
uv run psalter init
uv run psalter psalm add 23 --translation-id esv --verse "1:The LORD is my shepherd."
uv run python scripts/seed_psalms_from_api.py --translation BSB --psalm 23 --psalm 90
uv run psalter psalm list
uv run psalter psalm show 23
uv run psalter learn 23
uv run psalter progress
uv run psalter review
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Normal workflow notes:

- Passages are internal learning sections generated automatically from Psalm verses.
- `psalter learn 23` resumes the active section for Psalm 23; you do not need to remember a passage ID.
- When all sections are learned, the Psalm enters whole-Psalm consolidation before it is marked learned.
- `psalter passage list --psalm 23` and `psalter passage show ...` remain available for inspection.
- `psalter passage add` is an advanced partial-import tool. Once a Psalm is created that way, upgrading it to a complete Psalm import is not supported yet.

When `psalter learn` reaches recitation, choose `typed` or `spoken`.

Typed mode keeps the same `.done` multiline workflow.

Spoken mode runs completely locally. Prerequisites:

- A local recorder executable (ffmpeg recommended).
- A local whisper.cpp CLI executable.
- A local whisper model file (`.bin`).

No model is bundled and no model or audio is downloaded automatically.

Set configuration with environment variables:

```bash
export PSALTER_WHISPER_EXECUTABLE=/path/to/whisper-cli
export PSALTER_WHISPER_MODEL=/path/to/ggml-base.en.bin
export PSALTER_WHISPER_LANGUAGE=en
export PSALTER_WHISPER_THREADS=4
export PSALTER_RECORDER_EXECUTABLE=/path/to/ffmpeg
export PSALTER_AUDIO_INPUT_DEVICE="audio=Microphone Array (Realtek Audio)"
export PSALTER_RETAIN_AUDIO=0
```

Then run:

```bash
uv run psalter learn 23
```

During spoken recitation:

1. Press Enter to begin recording.
2. Recite from memory without viewing canonical text.
3. Press Enter to stop.

Temporary artifacts are deleted by default. Set `PSALTER_RETAIN_AUDIO=1` to retain local artifacts for debugging.

Transcription remains textual-only assessment. Pronunciation, cadence, and acoustic quality are not graded.

Known limitations:

- Recorder device names vary by platform.
- whisper.cpp errors can be environment or memory related.
- Assessment thresholds remain provisional.
- Tested recording command construction currently targets ffmpeg on desktop platforms.

Assessment currently performs textual normalization/alignment only. It does not evaluate pronunciation and does not accept semantic paraphrase substitutions.

## Psalm seeding script

You can seed complete Psalms directly from the bible.helloao.org API:

```bash
uv run python scripts/seed_psalms_from_api.py \
  --translation BSB \
  --book PSA \
  --psalm 23 \
  --psalm 121
```

Options:

- `--data-dir`: override psalter data directory.

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