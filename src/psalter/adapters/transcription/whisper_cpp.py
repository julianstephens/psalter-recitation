from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from psalter.adapters.process_runner import run_process
from psalter.application.dto import AudioArtifact, TranscriptArtifact
from psalter.application.errors import (
    TranscriptEmptyError,
    TranscriptOutputMissingError,
    WhisperExecutableNotFoundError,
    WhisperModelNotFoundError,
    WhisperProcessFailedError,
)
from psalter.config import WhisperCppConfig

_SIDE_CAR_SUFFIXES = (".json", ".srt", ".vtt", ".csv", ".lrc")


class WhisperCppTranscriber:
    def __init__(self, config: WhisperCppConfig) -> None:
        self._config = config

    def transcribe(self, artifact: AudioArtifact) -> TranscriptArtifact:
        self._validate_paths(artifact.path)
        output_base = self._create_output_base(artifact.path)
        try:
            args = self._build_args(artifact.path, output_base)
            result = run_process(args)
            if result.returncode != 0:
                raise WhisperProcessFailedError(
                    f"whisper.cpp failed with exit code {result.returncode}. "
                    f"Executable: {self._config.executable_path}. "
                    f"Model: {self._config.model_path}. "
                    f"stderr: {_stderr_excerpt(result.stderr)}"
                )
            output_path = output_base.with_suffix(".txt")
            if not output_path.exists():
                raise TranscriptOutputMissingError(
                    f"Expected transcript output file was not created: {output_path}"
                )
            text = output_path.read_text(encoding="utf-8").strip()
            if not text:
                raise TranscriptEmptyError(f"Transcript output is empty: {output_path}")
            retained_path = output_path if self._config.retain_artifacts else None
            return TranscriptArtifact(
                text=text,
                provider="whisper.cpp",
                model=str(self._config.model_path),
                raw_output_path=retained_path,
            )
        finally:
            self._cleanup_output_if_needed(output_base)

    def _validate_paths(self, audio_path: Path) -> None:
        if not self._config.executable_path.exists():
            raise WhisperExecutableNotFoundError(
                f"whisper executable not found: {self._config.executable_path}"
            )
        if not os.access(self._config.executable_path, os.X_OK):
            raise WhisperExecutableNotFoundError(
                f"whisper executable is not runnable: {self._config.executable_path}"
            )
        if not self._config.model_path.exists():
            raise WhisperModelNotFoundError(
                f"whisper model not found: {self._config.model_path}"
            )
        if not audio_path.exists():
            raise TranscriptOutputMissingError(f"Audio artifact does not exist: {audio_path}")
        if audio_path.stat().st_size == 0:
            raise TranscriptOutputMissingError(f"Audio artifact is empty: {audio_path}")

    def _create_output_base(self, audio_path: Path) -> Path:
        suffixless = audio_path.stem
        temp_dir = self._config.temp_directory
        fd, raw_path = tempfile.mkstemp(prefix=f"{suffixless}-", suffix=".whisper", dir=temp_dir)
        os.close(fd)
        base = Path(raw_path)
        base.unlink(missing_ok=True)
        return base

    def _build_args(self, audio_path: Path, output_base: Path) -> list[str]:
        args = [
            str(self._config.executable_path),
            "--model",
            str(self._config.model_path),
            "--file",
            str(audio_path),
            "--language",
            self._config.language,
            "--output-txt",
            "--output-file",
            str(output_base),
            "--no-timestamps",
        ]
        if self._config.threads is not None:
            args.extend(["--threads", str(self._config.threads)])
        return args

    def _cleanup_output(self, output_base: Path) -> None:
        output_base.with_suffix(".txt").unlink(missing_ok=True)
        for suffix in _SIDE_CAR_SUFFIXES:
            output_base.with_suffix(suffix).unlink(missing_ok=True)

    def _cleanup_output_if_needed(self, output_base: Path) -> None:
        if self._config.retain_artifacts:
            return
        cleanup_errors: list[str] = []
        for path in (output_base.with_suffix(".txt"),) + tuple(
            output_base.with_suffix(suffix) for suffix in _SIDE_CAR_SUFFIXES
        ):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                cleanup_errors.append(f"{path}: {exc}")
        if cleanup_errors and sys.exc_info()[0] is None:
            raise TranscriptOutputMissingError(
                "Failed to clean transcription artifacts: " + "; ".join(cleanup_errors)
            )


def _stderr_excerpt(stderr: str) -> str:
    compact = " ".join(stderr.split())
    return compact[:300]
