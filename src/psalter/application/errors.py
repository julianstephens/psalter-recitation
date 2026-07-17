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


class PsalmNotFoundError(ApplicationError):
    """Raised when a requested Psalm does not exist."""


class PsalmAlreadyExistsError(ApplicationError):
    """Raised when creating a Psalm that already exists."""


class PsalmTranslationAmbiguousError(ApplicationError):
    """Raised when Psalm translation resolution is ambiguous."""


class PsalmIncompleteError(ApplicationError):
    """Raised when a complete-Psalm operation requires complete Psalm data."""


class PsalmSegmentationConflictError(ApplicationError):
    """Raised when Psalm segmentation would conflict with existing state."""


class PsalmLearningPlanConflictError(ApplicationError):
    """Raised when a Psalm learning plan write conflicts with current state."""


class NoActivePassageError(ApplicationError):
    """Raised when a Psalm plan has no active passage to resolve."""


class WholePsalmConsolidationUnavailableError(ApplicationError):
    """Raised when whole-Psalm consolidation is unavailable."""


class LearningSessionNotFoundError(ApplicationError):
    """Raised when a learning session does not exist."""


class InvalidLearningTransitionError(ApplicationError):
    """Raised when a learning transition is invalid."""


class StaleLearningTargetError(ApplicationError):
    """Raised when a workflow action uses a stale active target token."""


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


class InstallationNotReadyError(ApplicationError):
    """Raised when commands require a ready installation."""


class InstallationIncompleteError(ApplicationError):
    """Raised when installation was started but not completed."""


class InstallationAlreadyReadyError(ApplicationError):
    """Raised when attempting initialization on a ready installation."""


class TranslationSelectionRequiredError(ApplicationError):
    """Raised when a translation is required but not provided."""


class TranslationNotSupportedError(ApplicationError):
    """Raised when a translation ID is unavailable from the provider."""


class CatalogInstallationFailedError(ApplicationError):
    """Raised when catalog import fails."""


class CatalogValidationFailedError(ApplicationError):
    """Raised when catalog import validation fails."""


class CatalogRepairUnsafeError(ApplicationError):
    """Raised when repair would invalidate learning history."""


class ScriptureProviderUnavailableError(ApplicationError):
    """Raised when the scripture provider is unavailable."""


class TranslationCatalogUnavailableError(ApplicationError):
    """Raised when translation catalog retrieval fails."""


class PsalmDownloadFailedError(ApplicationError):
    """Raised when a Psalm cannot be downloaded."""


class PsalmPayloadInvalidError(ApplicationError):
    """Raised when provider Psalm payload is malformed."""


class TranslationChangeBlockedError(ApplicationError):
    """Raised when translation replacement is blocked by policy."""
