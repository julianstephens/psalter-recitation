from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import BinaryIO

from psalter.application.dto import AudioArtifact, PreparedAudioUpload
from psalter.application.errors import AudioArtifactInvalidError, AudioRecordingFailedError
from psalter.config import FfmpegRecorderConfig

_CONTENT_TYPE_SUFFIXES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".mp4",
    "audio/aac": ".aac",
}


class FfmpegUploadedAudioPreparer:
    def __init__(self, config: FfmpegRecorderConfig) -> None:
        self._config = config

    def prepare(
        self,
        *,
        passage_id: str,
        source: BinaryIO,
        content_type: str,
    ) -> PreparedAudioUpload:
        source_path = self._build_source_path(passage_id, content_type)
        output_path = self._build_output_path(passage_id)
        try:
            with source_path.open("wb") as handle:
                source.seek(0)
                while chunk := source.read(1024 * 1024):
                    handle.write(chunk)
            self._convert(source_path, output_path)
            if not output_path.exists():
                raise AudioArtifactInvalidError(
                    f"Converted audio file was not created: {output_path}"
                )
            if output_path.stat().st_size == 0:
                raise AudioArtifactInvalidError(f"Converted audio file is empty: {output_path}")
            return PreparedAudioUpload(
                artifact=AudioArtifact(
                    path=output_path,
                    sample_rate_hz=16_000,
                    channels=1,
                    duration_seconds=_read_wav_duration(output_path),
                ),
                cleanup_paths=(source_path,),
            )
        except OSError as exc:
            raise AudioRecordingFailedError(
                f"Unable to prepare uploaded audio with {self._config.executable_path}: {exc}"
            ) from exc

    def _build_source_path(self, passage_id: str, content_type: str) -> Path:
        suffix = _CONTENT_TYPE_SUFFIXES.get(content_type, ".bin")
        fd, raw_path = tempfile.mkstemp(
            prefix=f"psalter-upload-{passage_id.replace('/', '-')}-",
            suffix=suffix,
            dir=self._config.temp_directory,
        )
        os.close(fd)
        return Path(raw_path)

    def _build_output_path(self, passage_id: str) -> Path:
        fd, raw_path = tempfile.mkstemp(
            prefix=f"psalter-upload-{passage_id.replace('/', '-')}-",
            suffix=".wav",
            dir=self._config.temp_directory,
        )
        os.close(fd)
        path = Path(raw_path)
        path.unlink(missing_ok=True)
        return path

    def _convert(self, source_path: Path, output_path: Path) -> None:
        process = subprocess.run(
            [
                str(self._config.executable_path),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if process.returncode != 0:
            raise AudioRecordingFailedError(
                f"ffmpeg failed with exit code {process.returncode}. "
                f"Executable: {self._config.executable_path}. "
                f"stderr: {_stderr_excerpt(process.stderr)}"
            )


def _read_wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return None
            return frames / float(frame_rate)
    except (wave.Error, OSError):
        return None


def _stderr_excerpt(stderr: str) -> str:
    compact = " ".join(stderr.split())
    return compact[:300]
