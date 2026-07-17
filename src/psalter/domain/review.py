from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from psalter.domain.errors import InvariantViolationError


class ReviewStatus(StrEnum):
    LEARNING = "learning"
    ACTIVE = "active"
    REINFORCEMENT = "reinforcement"
    MASTERED = "mastered"


@dataclass(frozen=True, slots=True)
class ReviewState:
    passage_id: str
    station: int
    learned_at: datetime | None
    next_review_at: datetime | None
    status: ReviewStatus

    def __post_init__(self) -> None:
        if self.station < 0:
            raise InvariantViolationError("Review station must be non-negative")
