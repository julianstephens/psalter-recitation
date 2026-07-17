from psalter.application.dto import AudioArtifact
from psalter.application.errors import NotSupportedError


class UnsupportedAudioRecorder:
    def record(self, passage_id: str) -> AudioArtifact:
        raise NotSupportedError(
            "No audio recorder has been configured. "
            "Recording is intentionally unsupported in this scaffold."
        )
