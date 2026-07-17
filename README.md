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

## Web development

The browser UI lives in a separate `web/` workspace and talks to the Python application through
the FastAPI adapter in `src/psalter/web/`.

For local web development without Docker:

```bash
uv run uvicorn psalter.web.app:create_app --factory --reload
cd web
npm install
npm run dev
```

For a two-container development stack:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

For a production-style local build:

```bash
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

`psalter init` installs a complete translation catalog (Psalms 1-150), preserves verse
boundaries, generates internal learning sections, and stores one selected translation as the
default.

Additional translations can also be installed. The Psalter keeps exactly one default
translation for normal commands like `psalter learn 90`.

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

To install another translation and make it the default without an interactive prompt:

```bash
uv run psalter init --translation KJV --set-default
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
