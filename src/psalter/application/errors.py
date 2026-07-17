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
