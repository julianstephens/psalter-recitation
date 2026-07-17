from __future__ import annotations

from psalter.application.dto import DueReviewDTO
from psalter.ports.clock import Clock
from psalter.ports.review_repository import ReviewRepository


class ReviewService:
    def __init__(self, reviews: ReviewRepository, clock: Clock) -> None:
        self._reviews = reviews
        self._clock = clock

    def get_due_reviews(self) -> list[DueReviewDTO]:
        due = self._reviews.list_due(self._clock.now())
        return [
            DueReviewDTO(
                passage_id=item.passage_id,
                station=item.station,
                next_review_at=item.next_review_at,
            )
            for item in due
        ]
