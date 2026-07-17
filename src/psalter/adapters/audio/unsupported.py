from psalter.application.dto import AudioArtifact, AudioRecordingRequest
from psalter.application.errors import AudioRecorderNotConfiguredError


class UnsupportedAudioRecorder:
    def record(self, request: AudioRecordingRequest) -> AudioArtifact:
        raise AudioRecorderNotConfiguredError(
            "Spoken recitation is not configured: PSALTER_RECORDER_EXECUTABLE is required."
        )
