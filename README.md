# psalter-recitation

A CLI-first application for Psalm memorization and review.

## Purpose

This project models and orchestrates a learning flow:

1. Exposure: show the complete canonical passage.
2. Practice: progress through deterministic masking levels.
3. Typed recitation: submit unaided text (`.done` ends multiline input).
4. Spoken recitation: record local microphone audio, transcribe with local whisper.cpp.
4. Assessment: normalize and align text with weighted scoring.
5. Confirmation: require two passing unaided recitations before learned.
6. Scheduling: create initial review one day after learning.

The CLI and any future UI must share the same application services and domain model.

## Status

Implemented:

- Ports-and-adapters structure with inward dependency direction.
- Typed domain models and state transitions.
- Application services for passage management, learning workflow, typed recitation assessment, review lookup, and progress.
- Spoken recitation orchestration that records audio and submits whisper transcript through the same recitation service path.
- SQLite adapter with tracked SQL migrations.
- Typer commands: init, passage add/list/show, learn, review, progress.
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
uv run psalter passage add --translation-id esv --psalm 23 --start-verse 1 --end-verse 1 --text "The LORD is my shepherd."
uv run psalter passage list
uv run psalter passage show esv-psalm-23-1-1
uv run psalter learn esv-psalm-23-1-1
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

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
uv run psalter learn esv-psalm-23-1-1
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