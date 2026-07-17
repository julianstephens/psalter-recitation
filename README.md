# psalter-recitation

A CLI-first application for Psalm memorization and review.

## Setup

```bash
uv sync
uv run psalter init
uv run psalter learn 90
uv run psalter progress
uv run psalter review
```

`psalter init` installs one complete translation catalog (Psalms 1-150), preserves verse
boundaries, generates internal learning sections, and stores the selected translation as the
default.

After initialization, `psalter learn 90` works without a translation flag.

Typed recitation requires no audio tooling. Spoken recitation remains optional and local-only
through ffmpeg + whisper.cpp configuration.

## Command surface

```text
psalter init
psalter learn PSALM_NUMBER
psalter progress
psalter review
psalter psalm list
psalter psalm show PSALM_NUMBER
psalter settings
```

## Debug logging

Application diagnostics are disabled during normal use. Enable debug logs on stderr for one
invocation with:

```bash
uv run psalter --debug init --resume
```

Or configure a persistent minimum level:

```bash
export PSALTER_LOG_LEVEL=DEBUG
uv run psalter progress
```

`--log-level` overrides the environment for one invocation. Debug events cover application
startup, dependency composition, scripture-provider requests, catalog acquisition, and other
application boundaries. Recitation text, Psalm contents, model files, and audio contents are not
written to logs.

## Recovery

If installation is interrupted:

```bash
uv run psalter init --resume
```

To repair missing or invalid Psalm bundles:

```bash
uv run psalter init --repair
```

## Advanced

Manual import and low-level passage inspection remain available for advanced workflows:

- `psalter psalm add`
- `psalter passage add|list|show`
- `scripts/seed_psalms_from_api.py` (thin wrapper around the same catalog installer)

## Project structure

```text
src/psalter/
    cli/
    application/
    domain/
    ports/
    adapters/
```
