from __future__ import annotations

from psalter.application.dto import ProgressSummaryDTO
from psalter.domain.learning import LearningPhase
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.recitation_repository import RecitationRepository
from psalter.ports.review_repository import ReviewRepository


class ProgressService:
    def __init__(
        self,
        passages: PassageRepository,
        sessions: LearningRepository,
        attempts: RecitationRepository,
        reviews: ReviewRepository,
        clock: Clock,
    ) -> None:
        self._passages = passages
        self._sessions = sessions
        self._attempts = attempts
        self._reviews = reviews
        self._clock = clock

    def summary(self) -> ProgressSummaryDTO:
        due_count = len(self._reviews.list_due(self._clock.now()))
        exposure = self._sessions.count_by_phase(LearningPhase.EXPOSURE)
        practice = self._sessions.count_by_phase(LearningPhase.PRACTICE)
        ready = self._sessions.count_by_phase(LearningPhase.READY_FOR_RECITATION)
        reinforcement = self._sessions.count_by_phase(LearningPhase.NEEDS_REINFORCEMENT)
        learned = self._sessions.count_by_phase(LearningPhase.LEARNED)
        seen = self._sessions.count_all()
        total = self._passages.count_all()
        return ProgressSummaryDTO(
            total_passages=total,
            unseen_passages=max(0, total - seen),
            exposure_passages=exposure,
            practice_passages=practice,
            ready_passages=ready,
            reinforcement_passages=reinforcement,
            learned_passages=learned,
            reviews_due=due_count,
            total_recitation_attempts=self._attempts.count_all(),
            successful_recitation_attempts=self._attempts.count_successful(),
        )
