from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import wave
from collections.abc import Callable
from pathlib import Path

from psalter.application.dto import AudioArtifact, AudioRecordingRequest
from psalter.application.errors import (
    AudioArtifactInvalidError,
    AudioRecordingFailedError,
    UnsupportedAudioPlatformError,
)
from psalter.config import FfmpegRecorderConfig

_DEFAULT_SAMPLE_RATE = 16_000
_DEFAULT_CHANNELS = 1
_MIN_RECORDING_SECONDS = 0.2


class FfmpegAudioRecorder:
    def __init__(self, config: FfmpegRecorderConfig) -> None:
        self._config = config

    def record(self, request: AudioRecordingRequest) -> AudioArtifact:
        output_path = self._build_output_path(request.passage_id)
        args = self._build_args(output_path)
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
            stop_requested = False
            if request.wait_for_stop is not None:
                stop_requested = self._wait_for_stop_or_process_exit(
                    process=process,
                    wait_for_stop=request.wait_for_stop,
                )
            else:
                process.wait(timeout=self._config.max_duration_seconds)
            if stop_requested:
                self._request_stop(process)
            _, stderr = process.communicate(timeout=10)
            if process.returncode not in (0, 255):
                raise AudioRecordingFailedError(
                    f"Recorder failed with exit code {process.returncode}. "
                    f"Executable: {self._config.executable_path}. "
                    f"stderr: {_stderr_excerpt(stderr)}"
                )
            if not output_path.exists():
                raise AudioArtifactInvalidError(
                    f"Recorder did not create audio file: {output_path}"
                )
            if output_path.stat().st_size == 0:
                raise AudioArtifactInvalidError(
                    f"Recorder produced empty audio file: {output_path}"
                )
            duration = _read_wav_duration(output_path)
            if duration is not None and duration < _MIN_RECORDING_SECONDS:
                raise AudioArtifactInvalidError(
                    "Recording too short "
                    f"({duration:.3f}s); minimum is {_MIN_RECORDING_SECONDS:.1f}s."
                )
            return AudioArtifact(
                path=output_path,
                sample_rate_hz=request.sample_rate_hz,
                channels=request.channels,
                duration_seconds=duration,
            )
        except KeyboardInterrupt as exc:
            if process is not None:
                self._terminate_process(process)
            raise AudioRecordingFailedError("Recording interrupted.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AudioRecordingFailedError("Recorder process did not stop cleanly.") from exc
        except OSError as exc:
            raise AudioRecordingFailedError(
                f"Unable to execute recorder at {self._config.executable_path}: {exc}"
            ) from exc
        finally:
            if process is not None and process.poll() is None:
                self._terminate_process(process)

    def _build_output_path(self, passage_id: str) -> Path:
        prefix = f"psalter-{passage_id.replace('/', '-')}-"
        temp_dir = self._config.temp_directory
        fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".wav", dir=temp_dir)
        os.close(fd)
        Path(raw_path).unlink(missing_ok=True)
        return Path(raw_path)

    def _build_args(self, output_path: Path) -> list[str]:
        executable = str(self._config.executable_path)
        base = [
            executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
        ]
        if self._config.max_duration_seconds is not None:
            base.extend(["-t", str(self._config.max_duration_seconds)])
        base.extend(self._input_args())
        base.extend(
            [
                "-ac",
                str(_DEFAULT_CHANNELS),
                "-ar",
                str(_DEFAULT_SAMPLE_RATE),
                "-sample_fmt",
                "s16",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
        )
        return base

    def _input_args(self) -> list[str]:
        platform = sys.platform
        device = self._config.input_device
        if platform.startswith("win"):
            return ["-f", "dshow", "-i", device or "audio=default"]
        if platform.startswith("linux"):
            return ["-f", "alsa", "-i", device or "default"]
        if platform == "darwin":
            return ["-f", "avfoundation", "-i", device or ":0"]
        raise UnsupportedAudioPlatformError(
            f"Audio recording is unsupported on platform: {platform}"
        )

    def _request_stop(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None or process.stdin is None:
            return
        try:
            process.stdin.write("q\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            return

    def _terminate_process(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def _wait_for_stop_or_process_exit(
        self,
        *,
        process: subprocess.Popen[str],
        wait_for_stop: Callable[[float | None], bool],
    ) -> bool:
        poll_interval = 0.1
        while process.poll() is None:
            if wait_for_stop(poll_interval):
                return True
        return False


def _read_wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return None
            return frames / float(frame_rate)
    except wave.Error, OSError:
        return None


def _stderr_excerpt(stderr: str) -> str:
    compact = " ".join(stderr.split())
    return compact[:300]
