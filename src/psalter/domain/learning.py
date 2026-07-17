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
    updated_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if self.practice_level < 0:
            raise InvariantViolationError("Practice level must be non-negative")
        if self.successful_blank_recitations < 0:
            raise InvariantViolationError("Successful blank recitations must be non-negative")
        if self.phase is LearningPhase.LEARNED and self.completed_at is None:
            raise InvariantViolationError("Learned sessions must have completed_at")
        if self.phase is not LearningPhase.LEARNED and self.completed_at is not None:
            raise InvariantViolationError("Only learned sessions can have completed_at")

    def begin_exposure(self, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.UNSEEN:
            raise InvalidTransitionError("Only unseen sessions can enter exposure")
        return replace(self, phase=LearningPhase.EXPOSURE, updated_at=when)

    def complete_exposure(self, when: datetime, *, skip_practice: bool = False) -> LearningSession:
        if self.phase is not LearningPhase.EXPOSURE:
            raise InvalidTransitionError("Only exposure sessions can enter practice")
        next_phase = LearningPhase.READY_FOR_RECITATION if skip_practice else LearningPhase.PRACTICE
        return replace(self, phase=next_phase, updated_at=when)

    def advance_practice_level(self, max_level: int, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.PRACTICE:
            raise InvalidTransitionError("Practice level can only advance in practice phase")
        if max_level < 0:
            raise InvariantViolationError("Maximum practice level must be non-negative")
        if self.practice_level >= max_level:
            raise InvalidTransitionError("Practice level already at maximum")
        next_level = self.practice_level + 1
        if next_level >= max_level:
            return self.mark_practice_ready(when)
        return replace(self, practice_level=next_level, updated_at=when)

    def mark_practice_ready(self, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.PRACTICE:
            raise InvalidTransitionError("Only practice sessions can become ready for recitation")
        return replace(self, phase=LearningPhase.READY_FOR_RECITATION, updated_at=when)

    def record_successful_recitation(self, required_passes: int, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.READY_FOR_RECITATION:
            raise InvalidTransitionError("Only ready sessions can record successful recitation")
        if required_passes <= 0:
            raise InvariantViolationError("Required pass count must be positive")
        total_successes = self.successful_blank_recitations + 1
        if total_successes >= required_passes:
            return replace(
                self,
                phase=LearningPhase.LEARNED,
                successful_blank_recitations=total_successes,
                updated_at=when,
                completed_at=when,
            )
        return replace(
            self,
            successful_blank_recitations=total_successes,
            updated_at=when,
        )

    def mark_needs_reinforcement(self, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.READY_FOR_RECITATION:
            raise InvalidTransitionError("Only ready sessions can require reinforcement")
        return replace(self, phase=LearningPhase.NEEDS_REINFORCEMENT, updated_at=when)

    def resume_practice(self, when: datetime) -> LearningSession:
        if self.phase is not LearningPhase.NEEDS_REINFORCEMENT:
            raise InvalidTransitionError("Only reinforcement sessions can resume practice")
        return replace(self, phase=LearningPhase.PRACTICE, updated_at=when)
