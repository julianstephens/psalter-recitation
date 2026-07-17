from __future__ import annotations

from psalter.application.dto import ProgressSummaryDTO
from psalter.domain.learning import LearningPhase
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.review_repository import ReviewRepository


class ProgressService:
    def __init__(
        self,
        passages: PassageRepository,
        sessions: LearningRepository,
        reviews: ReviewRepository,
        clock: Clock,
    ) -> None:
        self._passages = passages
        self._sessions = sessions
        self._reviews = reviews
        self._clock = clock

    def summary(self) -> ProgressSummaryDTO:
        due_count = len(self._reviews.list_due(self._clock.now()))
        return ProgressSummaryDTO(
            total_passages=self._passages.count_all(),
            passages_currently_learning=self._sessions.count_by_phase(LearningPhase.PRACTICE)
            + self._sessions.count_by_phase(LearningPhase.EXPOSURE)
            + self._sessions.count_by_phase(LearningPhase.READY_FOR_RECITATION)
            + self._sessions.count_by_phase(LearningPhase.NEEDS_REINFORCEMENT),
            passages_learned=self._sessions.count_by_phase(LearningPhase.LEARNED),
            reviews_due=due_count,
        )
