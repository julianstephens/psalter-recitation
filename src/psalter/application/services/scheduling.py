from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from psalter.domain.review import ReviewState, ReviewStatus


@dataclass(frozen=True, slots=True)
class InitialReviewSchedulingPolicy:
    first_station: int = 1
    initial_delay: timedelta = timedelta(days=1)

    def create_initial_state(self, passage_id: str, learned_at: datetime) -> ReviewState:
        next_review_at = learned_at + self.initial_delay
        return ReviewState(
            passage_id=passage_id,
            station=self.first_station,
            learned_at=learned_at,
            next_review_at=next_review_at,
            status=ReviewStatus.ACTIVE,
        )
