from psalter.application.dto import AudioArtifact, TranscriptDTO
from psalter.application.errors import NotSupportedError


class UnsupportedTranscriber:
    def transcribe(self, artifact: AudioArtifact) -> TranscriptDTO:
        raise NotSupportedError(
            "No transcription provider has been configured. "
            "Transcription is intentionally unsupported in this scaffold."
        )
