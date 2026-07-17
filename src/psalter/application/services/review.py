from __future__ import annotations

from psalter.application.dto import DueReviewDTO, PsalmReviewItemDTO
from psalter.domain.passage import PassageKind
from psalter.ports.clock import Clock
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.psalm_repository import PsalmRepository
from psalter.ports.review_repository import ReviewRepository


class ReviewService:
    def __init__(
        self,
        reviews: ReviewRepository,
        clock: Clock,
        passages: PassageRepository,
        psalms: PsalmRepository,
    ) -> None:
        self._reviews = reviews
        self._clock = clock
        self._passages = passages
        self._psalms = psalms

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

    def get_due_psalm_reviews(self) -> list[PsalmReviewItemDTO]:
        items: list[PsalmReviewItemDTO] = []
        for due in self._reviews.list_due(self._clock.now()):
            passage = self._passages.get_by_id(due.passage_id)
            if passage is None:
                continue
            psalm = self._psalms.get_by_id(passage.psalm_id)
            if psalm is None:
                continue
            items.append(
                PsalmReviewItemDTO(
                    psalm_id=psalm.id,
                    translation_id=psalm.translation_id,
                    psalm_number=psalm.psalm_number,
                    reason=(
                        "consolidation review"
                        if passage.kind is PassageKind.CONSOLIDATION
                        else "section review"
                    ),
                    due_label=(
                        "complete Psalm"
                        if passage.kind is PassageKind.CONSOLIDATION
                        else (
                            f"verse {passage.start_verse}"
                            if passage.start_verse == passage.end_verse
                            else f"verses {passage.start_verse}-{passage.end_verse}"
                        )
                    ),
                    next_review_at=due.next_review_at,
                    passage_id=passage.id,
                )
            )
        items.sort(key=lambda item: item.next_review_at or self._clock.now())
        return items
