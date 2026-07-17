import pytest

from psalter.adapters.audio.unsupported import UnsupportedAudioRecorder
from psalter.adapters.transcription.unsupported import UnsupportedTranscriber
from psalter.application.dto import AudioArtifact
from psalter.application.errors import NotSupportedError


def test_unsupported_audio_recorder_raises() -> None:
    with pytest.raises(NotSupportedError):
        UnsupportedAudioRecorder().record("p1")


def test_unsupported_transcriber_raises() -> None:
    with pytest.raises(NotSupportedError):
        UnsupportedTranscriber().transcribe(AudioArtifact(uri="file:///tmp/a.wav"))
