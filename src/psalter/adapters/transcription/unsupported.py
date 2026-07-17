from psalter.application.dto import AudioArtifact, TranscriptArtifact
from psalter.application.errors import TranscriberNotConfiguredError


class UnsupportedTranscriber:
    def transcribe(self, artifact: AudioArtifact) -> TranscriptArtifact:
        raise TranscriberNotConfiguredError(
            "Spoken recitation is not configured: "
            "PSALTER_WHISPER_EXECUTABLE and PSALTER_WHISPER_MODEL are required."
        )
