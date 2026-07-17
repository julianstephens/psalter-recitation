from pathlib import Path

import pytest

from psalter.adapters.audio.unsupported import UnsupportedAudioRecorder
from psalter.adapters.transcription.unsupported import UnsupportedTranscriber
from psalter.application.dto import AudioArtifact, AudioRecordingRequest
from psalter.application.errors import (
    AudioRecorderNotConfiguredError,
    TranscriberNotConfiguredError,
)


def test_unsupported_audio_recorder_raises() -> None:
    with pytest.raises(AudioRecorderNotConfiguredError):
        UnsupportedAudioRecorder().record(
            AudioRecordingRequest(passage_id="p1", sample_rate_hz=16000, channels=1)
        )


def test_unsupported_transcriber_raises() -> None:
    with pytest.raises(TranscriberNotConfiguredError):
        UnsupportedTranscriber().transcribe(
            AudioArtifact(
                path=Path(__file__), sample_rate_hz=16000, channels=1, duration_seconds=1.0
            )
        )
