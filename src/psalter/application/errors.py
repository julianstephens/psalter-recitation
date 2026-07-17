class ApplicationError(Exception):
    """Base error for application-level failures."""


class NotFoundError(ApplicationError):
    """Raised when an expected entity does not exist."""


class NotSupportedError(ApplicationError):
    """Raised when a configured capability is intentionally unavailable."""
