class DomainError(Exception):
    """Base error for domain-level failures."""


class InvariantViolationError(DomainError):
    """Raised when an entity invariant is violated."""


class InvalidTransitionError(DomainError):
    """Raised when a state transition is not permitted."""
