from __future__ import annotations

from pathlib import Path

import pytest

from psalter.adapters.process_runner import ProcessResult
from psalter.adapters.transcription.whisper_cpp import WhisperCppTranscriber
from psalter.application.dto import AudioArtifact
from psalter.application.errors import (
    TranscriptEmptyError,
    TranscriptOutputMissingError,
    WhisperModelNotFoundError,
    WhisperProcessFailedError,
)
from psalter.config import WhisperCppConfig


def _audio(path: Path) -> AudioArtifact:
    path.write_bytes(b"wav")
    return AudioArtifact(path=path, sample_rate_hz=16000, channels=1, duration_seconds=1.0)


def _config(tmp_path: Path, model_path: Path) -> WhisperCppConfig:
    return WhisperCppConfig(
        executable_path=Path(__file__),
        model_path=model_path,
        language="en",
        threads=4,
        temp_directory=tmp_path,
    )


def test_whisper_transcriber_builds_expected_args_and_reads_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"m")
    audio = _audio(tmp_path / "input.wav")
    captured_args: list[list[str]] = []

    def _fake_run(
        args: list[str], *, cwd: Path | None = None, timeout_seconds: float | None = None
    ) -> ProcessResult:
        captured_args.append(args)
        output_base = Path(args[args.index("--output-file") + 1])
        output_base.with_suffix(".txt").write_text("  transcript text  ", encoding="utf-8")
        return ProcessResult(args=tuple(args), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "psalter.adapters.transcription.whisper_cpp.run_process",
        _fake_run,
    )
    monkeypatch.setattr("os.access", lambda *_args, **_kwargs: True)

    transcriber = WhisperCppTranscriber(_config(tmp_path, model))
    transcript = transcriber.transcribe(audio)

    args = captured_args[0]
    assert args[0] == str(Path(__file__))
    assert "--model" in args and str(model) in args
    assert "--file" in args and str(audio.path) in args
    assert "--language" in args and "en" in args
    assert "--threads" in args and "4" in args
    assert transcript.text == "transcript text"
    assert transcript.provider == "whisper.cpp"


def test_whisper_transcriber_raises_when_model_missing(tmp_path: Path) -> None:
    audio = _audio(tmp_path / "input.wav")
    transcriber = WhisperCppTranscriber(_config(tmp_path, tmp_path / "missing-model.bin"))
    with pytest.raises(WhisperModelNotFoundError):
        transcriber.transcribe(audio)


def test_whisper_transcriber_raises_on_non_zero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"m")
    audio = _audio(tmp_path / "input.wav")

    monkeypatch.setattr(
        "psalter.adapters.transcription.whisper_cpp.run_process",
        lambda args, **kwargs: ProcessResult(tuple(args), 1, "", "boom"),
    )
    monkeypatch.setattr("os.access", lambda *_args, **_kwargs: True)

    transcriber = WhisperCppTranscriber(_config(tmp_path, model))
    with pytest.raises(WhisperProcessFailedError, match="exit code 1"):
        transcriber.transcribe(audio)


def test_whisper_transcriber_raises_when_output_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"m")
    audio = _audio(tmp_path / "input.wav")
    monkeypatch.setattr(
        "psalter.adapters.transcription.whisper_cpp.run_process",
        lambda args, **kwargs: ProcessResult(tuple(args), 0, "", ""),
    )
    monkeypatch.setattr("os.access", lambda *_args, **_kwargs: True)

    transcriber = WhisperCppTranscriber(_config(tmp_path, model))
    with pytest.raises(TranscriptOutputMissingError):
        transcriber.transcribe(audio)


def test_whisper_transcriber_raises_on_blank_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"m")
    audio = _audio(tmp_path / "input.wav")

    def _fake_run(args: list[str], **kwargs: object) -> ProcessResult:
        output_base = Path(args[args.index("--output-file") + 1])
        output_base.with_suffix(".txt").write_text("   ", encoding="utf-8")
        return ProcessResult(args=tuple(args), returncode=0, stdout="", stderr="")

    monkeypatch.setattr("psalter.adapters.transcription.whisper_cpp.run_process", _fake_run)
    monkeypatch.setattr("os.access", lambda *_args, **_kwargs: True)

    transcriber = WhisperCppTranscriber(_config(tmp_path, model))
    with pytest.raises(TranscriptEmptyError):
        transcriber.transcribe(audio)
