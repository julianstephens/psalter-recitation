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

## Add a passage

```bash
uv run psalter passage add \
  --translation-id esv \
  --psalm 23 \
  --start-verse 1 \
  --end-verse 1 \
  --text "The LORD is my shepherd."
```

List and show passages:

```bash
uv run psalter passage list
uv run psalter passage show esv-psalm-23-1-1
```

### Seed passages from the helloao API

```bash
uv run python scripts/seed_passages_from_api.py \
  --translation BSB \
  --book PSA \
  --passage 23:1-3 \
  --passage 121:1-2
```

Optional flags:

- `--data-dir /path/to/data`
- `--fail-on-existing`

## Learn workflow

```bash
uv run psalter learn esv-psalm-23-1-1
```

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
