from __future__ import annotations

import os
from pathlib import Path

import pytest

from psalter.adapters.transcription.whisper_cpp import WhisperCppTranscriber
from psalter.application.dto import AudioArtifact
from psalter.config import WhisperCppConfig


@pytest.mark.integration
def test_whisper_cpp_transcribes_fixture_when_enabled(tmp_path: Path) -> None:
    if os.getenv("PSALTER_RUN_WHISPER_INTEGRATION") != "1":
        pytest.skip("set PSALTER_RUN_WHISPER_INTEGRATION=1 to run whisper integration test")

    executable = os.getenv("PSALTER_WHISPER_EXECUTABLE")
    model = os.getenv("PSALTER_WHISPER_MODEL")
    fixture = os.getenv("PSALTER_WHISPER_FIXTURE_WAV")
    if not executable or not model or not fixture:
        pytest.skip(
            "PSALTER_WHISPER_EXECUTABLE, PSALTER_WHISPER_MODEL, and "
            "PSALTER_WHISPER_FIXTURE_WAV are required for integration test"
        )

    fixture_path = Path(fixture)
    if not fixture_path.exists():
        pytest.skip(f"Whisper fixture does not exist: {fixture_path}")

    artifact = AudioArtifact(
        path=fixture_path,
        sample_rate_hz=16000,
        channels=1,
        duration_seconds=None,
    )
    transcriber = WhisperCppTranscriber(
        WhisperCppConfig(
            executable_path=Path(executable),
            model_path=Path(model),
            language=os.getenv("PSALTER_WHISPER_LANGUAGE", "en"),
            threads=None,
            temp_directory=tmp_path,
            retain_artifacts=False,
        )
    )
    transcript = transcriber.transcribe(artifact)
    assert transcript.text.strip()
