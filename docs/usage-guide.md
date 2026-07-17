# Usage Guide

## Prerequisites

- Python 3.14+
- `uv`

For spoken recitation:

- local `ffmpeg` executable
- local `whisper.cpp` executable
- local whisper model file (`.bin`)

## Initial setup

```bash
uv sync
uv run psalter init
```

## Add or seed a Psalm

```bash
uv run psalter psalm add 23 \
  --translation-id esv \
  --verse "1:The LORD is my shepherd."
```

List and show Psalms:

```bash
uv run psalter psalm list
uv run psalter psalm show 23
```

Internal passages are generated automatically from verse boundaries. Advanced passage inspection remains available:

```bash
uv run psalter passage list --psalm 23
uv run psalter passage show esv-psalm-23-1-1
```

### Seed complete Psalms from the helloao API

```bash
uv run python scripts/seed_psalms_from_api.py \
  --translation BSB \
  --book PSA \
  --psalm 23 \
  --psalm 121
```

Optional flags:

- `--data-dir /path/to/data`

## Learn workflow

```bash
uv run psalter learn 23
```

The application chooses the internal section, resumes it automatically, and advances to the next section when learned. After all sections are learned, it enters complete-Psalm consolidation before marking the Psalm learned.

When recitation is reached, choose:

- `typed`
- `spoken`

### Typed recitation

Enter text and finish with `.done` on its own line.

### Spoken recitation

The CLI prompts:

1. Press Enter to begin recording.
2. Recite from memory.
3. Press Enter again to stop.
4. Local transcription runs and is assessed through the standard recitation path.

## Spoken configuration

Set environment variables before running spoken mode:

```bash
export PSALTER_WHISPER_EXECUTABLE=/path/to/whisper-cli
export PSALTER_WHISPER_MODEL=/path/to/ggml-base.en.bin
export PSALTER_WHISPER_LANGUAGE=en
export PSALTER_WHISPER_THREADS=4
export PSALTER_RECORDER_EXECUTABLE=/path/to/ffmpeg
export PSALTER_AUDIO_INPUT_DEVICE="audio=Microphone"
export PSALTER_RETAIN_AUDIO=0
```

Optional:

```bash
export PSALTER_AUDIO_TEMP_DIRECTORY=/path/to/temp
```

## Review and progress

```bash
uv run psalter review
uv run psalter progress
```

## Quality checks

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```
