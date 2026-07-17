from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from psalter.domain.errors import InvalidTransitionError, InvariantViolationError


class LearningPhase(StrEnum):
    UNSEEN = "unseen"
    EXPOSURE = "exposure"
    PRACTICE = "practice"
    READY_FOR_RECITATION = "ready_for_recitation"
    LEARNED = "learned"
    NEEDS_REINFORCEMENT = "needs_reinforcement"


@dataclass(frozen=True, slots=True)
class LearningSession:
    id: str
    passage_id: str
    phase: LearningPhase
    practice_level: int
    successful_blank_recitations: int
    started_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if self.practice_level < 0:
            raise InvariantViolationError("Practice level must be non-negative")
        if self.successful_blank_recitations < 0:
            raise InvariantViolationError("Successful blank recitations must be non-negative")

    def begin_exposure(self) -> LearningSession:
        if self.phase is not LearningPhase.UNSEEN:
            raise InvalidTransitionError("Only unseen sessions can enter exposure")
        return replace(self, phase=LearningPhase.EXPOSURE)

    def complete_exposure(self) -> LearningSession:
        if self.phase is not LearningPhase.EXPOSURE:
            raise InvalidTransitionError("Only exposure sessions can enter practice")
        return replace(self, phase=LearningPhase.PRACTICE)

    def mark_practice_ready(self) -> LearningSession:
        if self.phase is not LearningPhase.PRACTICE:
            raise InvalidTransitionError("Only practice sessions can become ready for recitation")
        return replace(self, phase=LearningPhase.READY_FOR_RECITATION)

    def mark_learned(self, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.READY_FOR_RECITATION:
            raise InvalidTransitionError("Only ready sessions can be marked learned")
        return replace(self, phase=LearningPhase.LEARNED, completed_at=when)

    def mark_needs_reinforcement(self) -> LearningSession:
        if self.phase is not LearningPhase.READY_FOR_RECITATION:
            raise InvalidTransitionError("Only ready sessions can require reinforcement")
        return replace(self, phase=LearningPhase.NEEDS_REINFORCEMENT)

    def resume_practice(self) -> LearningSession:
        if self.phase is not LearningPhase.NEEDS_REINFORCEMENT:
            raise InvalidTransitionError("Only reinforcement sessions can resume practice")
        return replace(self, phase=LearningPhase.PRACTICE)
