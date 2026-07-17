# Architecture

This project follows a ports-and-adapters design with a CLI entrypoint and a strict application/domain core.

## Layers

- **CLI (`src/psalter/cli`)**: command parsing, prompts, and output formatting.
- **Application (`src/psalter/application`)**: orchestration services, DTOs, and application errors.
- **Domain (`src/psalter/domain`)**: immutable entities, value constraints, and learning/recitation rules.
- **Ports (`src/psalter/ports`)**: interfaces for persistence, clock, audio recording, and transcription.
- **Adapters (`src/psalter/adapters`)**: concrete implementations for SQLite, system clock, ffmpeg recording, whisper.cpp transcription, and unsupported fallbacks.
- **Bootstrap (`src/psalter/bootstrap.py`)**: composition root that wires config, ports, adapters, and services.

## Core flow

1. User runs CLI command (`psalter ...`).
2. CLI builds a container with `build_container(...)`.
3. Application services execute use cases against domain models.
4. Persistence writes happen through repositories and a recitation commit boundary.

## Recitation paths

- **Typed recitation**: user submits multiline text, assessed by `RecitationService.submit_text(...)`.
- **Spoken recitation**:
  1. Record microphone audio via `FfmpegAudioRecorder`.
  2. Transcribe locally via `WhisperCppTranscriber`.
  3. Submit transcript through the same `RecitationService.submit_text(...)` path with `speech_transcript` source.

This keeps normalization, alignment, scoring, learning-state transitions, and persistence in one shared assessment pipeline.

## Data and migrations

- SQLite database is managed through explicit SQL migrations in:
  - `src/psalter/adapters/persistence/migrations/`
- `SqliteMigrator` applies pending migrations before command workflows.

## Configuration

Configuration is centralized in `src/psalter/config.py` and includes:

- data directory and database path
- recorder settings (ffmpeg executable, input device, limits)
- whisper.cpp settings (executable path, model path, language, threads)
- artifact retention behavior for spoken workflows
