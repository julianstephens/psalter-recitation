from __future__ import annotations

import io
from pathlib import Path

import pytest

from psalter.adapters.audio.ffmpeg import FfmpegAudioRecorder
from psalter.application.dto import AudioRecordingRequest
from psalter.application.errors import AudioArtifactInvalidError, AudioRecordingFailedError
from psalter.config import FfmpegRecorderConfig


class _FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdin = io.StringIO()
        self._terminated = False
        self.poll_count = 0

    def wait(self, timeout: int | None = None) -> int:
        return self.returncode

    def communicate(self, timeout: int | None = None) -> tuple[str, str]:
        return ("", "stderr output")

    def poll(self) -> int | None:
        self.poll_count += 1
        return None if not self._terminated else self.returncode

    def terminate(self) -> None:
        self._terminated = True

    def kill(self) -> None:
        self._terminated = True


def _config(tmp_path: Path) -> FfmpegRecorderConfig:
    return FfmpegRecorderConfig(
        executable_path=Path("ffmpeg"),
        input_device="audio=Microphone",
        max_duration_seconds=5,
        temp_directory=tmp_path,
    )


def test_ffmpeg_recorder_records_to_wav_with_expected_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_args: list[list[str]] = []
    fake_process = _FakeProcess(returncode=0)

    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        captured_args.append(args)
        output_path = Path(args[-1])
        output_path.write_bytes(b"wav-data")
        return fake_process

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    monkeypatch.setattr("psalter.adapters.audio.ffmpeg._read_wav_duration", lambda _: 1.0)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    artifact = recorder.record(
        AudioRecordingRequest(
            passage_id="p1",
            sample_rate_hz=16000,
            channels=1,
            wait_for_stop=lambda timeout=None: True,
        )
    )

    args = captured_args[0]
    assert args[0] == "ffmpeg"
    assert "-f" in args and "dshow" in args
    assert "-i" in args and "audio=Microphone" in args
    assert "-ac" in args and "1" in args
    assert "-ar" in args and "16000" in args
    assert artifact.path.suffix == ".wav"
    assert fake_process.stdin.getvalue() == "q\n"


def test_ffmpeg_recorder_raises_on_non_zero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        output_path = Path(args[-1])
        output_path.write_bytes(b"wav-data")
        return _FakeProcess(returncode=1)

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    monkeypatch.setattr("psalter.adapters.audio.ffmpeg._read_wav_duration", lambda _: 1.0)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    with pytest.raises(AudioRecordingFailedError, match="exit code 1"):
        recorder.record(
            AudioRecordingRequest(
                passage_id="p1",
                sample_rate_hz=16000,
                channels=1,
                wait_for_stop=lambda timeout=None: True,
            )
        )


def test_ffmpeg_recorder_raises_when_output_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", lambda args, **kwargs: _FakeProcess(returncode=0))

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    with pytest.raises(AudioArtifactInvalidError, match="did not create"):
        recorder.record(
            AudioRecordingRequest(
                passage_id="p1",
                sample_rate_hz=16000,
                channels=1,
                wait_for_stop=lambda timeout=None: True,
            )
        )


def test_ffmpeg_recorder_raises_when_zero_byte_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        Path(args[-1]).write_bytes(b"")
        return _FakeProcess(returncode=0)

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    with pytest.raises(AudioArtifactInvalidError, match="empty"):
        recorder.record(
            AudioRecordingRequest(
                passage_id="p1",
                sample_rate_hz=16000,
                channels=1,
                wait_for_stop=lambda timeout=None: True,
            )
        )


def test_ffmpeg_recorder_handles_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_process = _FakeProcess(returncode=0)

    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        Path(args[-1]).write_bytes(b"wav-data")
        return fake_process

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    with pytest.raises(AudioRecordingFailedError, match="interrupted"):
        recorder.record(
            AudioRecordingRequest(
                passage_id="p1",
                sample_rate_hz=16000,
                channels=1,
                wait_for_stop=lambda timeout=None: (_ for _ in ()).throw(KeyboardInterrupt()),
            )
        )
    assert fake_process._terminated


def test_ffmpeg_recorder_terminates_child_when_wait_callback_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_process = _FakeProcess(returncode=0)

    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        Path(args[-1]).write_bytes(b"wav-data")
        return fake_process

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    with pytest.raises(RuntimeError, match="wait callback failed"):
        recorder.record(
            AudioRecordingRequest(
                passage_id="p1",
                sample_rate_hz=16000,
                channels=1,
                wait_for_stop=lambda timeout=None: (_ for _ in ()).throw(
                    RuntimeError("wait callback failed")
                ),
            )
        )
    assert fake_process._terminated


def test_ffmpeg_recorder_does_not_write_stop_when_process_exits_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _ExitingProcess(_FakeProcess):
        def poll(self) -> int | None:
            self.poll_count += 1
            if self.poll_count >= 2:
                return self.returncode
            return None

    fake_process = _ExitingProcess(returncode=0)
    observed_timeouts: list[float | None] = []

    def _fake_popen(args: list[str], **kwargs: object) -> _ExitingProcess:
        Path(args[-1]).write_bytes(b"wav-data")
        return fake_process

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    monkeypatch.setattr("psalter.adapters.audio.ffmpeg._read_wav_duration", lambda _: 1.0)

    recorder = FfmpegAudioRecorder(_config(tmp_path))
    artifact = recorder.record(
        AudioRecordingRequest(
            passage_id="p1",
            sample_rate_hz=16000,
            channels=1,
            wait_for_stop=lambda timeout=None: observed_timeouts.append(timeout) or False,
        )
    )

    assert artifact.duration_seconds == 1.0
    assert fake_process.stdin.getvalue() == ""
    assert observed_timeouts and observed_timeouts[0] == 0.1
