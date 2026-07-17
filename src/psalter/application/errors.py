class ApplicationError(Exception):
    """Base error for application-level failures."""


class NotFoundError(ApplicationError):
    """Raised when an expected entity does not exist."""


class NotSupportedError(ApplicationError):
    """Raised when a configured capability is intentionally unavailable."""


class PassageNotFoundError(ApplicationError):
    """Raised when a requested passage does not exist."""


class PassageAlreadyExistsError(ApplicationError):
    """Raised when creating a passage that already exists."""


class LearningSessionNotFoundError(ApplicationError):
    """Raised when a learning session does not exist."""


class InvalidLearningTransitionError(ApplicationError):
    """Raised when a learning transition is invalid."""


class InvalidPassageError(ApplicationError):
    """Raised when passage input fails validation."""


class PersistenceConflictError(ApplicationError):
    """Raised when a write conflicts with current persistent state."""


class AudioRecorderNotConfiguredError(ApplicationError):
    """Raised when spoken recitation is requested without recorder configuration."""


class AudioRecordingFailedError(ApplicationError):
    """Raised when audio recording subprocess execution fails."""


class AudioArtifactInvalidError(ApplicationError):
    """Raised when a recorded artifact is missing or malformed."""


class TranscriberNotConfiguredError(ApplicationError):
    """Raised when spoken recitation is requested without transcriber configuration."""


class WhisperExecutableNotFoundError(ApplicationError):
    """Raised when the configured whisper executable cannot be used."""


class WhisperModelNotFoundError(ApplicationError):
    """Raised when the configured whisper model path does not exist."""


class WhisperProcessFailedError(ApplicationError):
    """Raised when whisper subprocess exits unsuccessfully or times out."""


class TranscriptOutputMissingError(ApplicationError):
    """Raised when whisper succeeds but no transcript output is produced."""


class TranscriptEmptyError(ApplicationError):
    """Raised when generated transcript output is blank."""


class ArtifactCleanupFailedError(ApplicationError):
    """Raised when temporary artifact cleanup fails."""


class UnsupportedAudioPlatformError(ApplicationError):
    """Raised when recorder platform command generation is unsupported."""
