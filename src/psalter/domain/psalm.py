from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from psalter.domain.errors import InvalidTransitionError, InvariantViolationError


class PsalmCompleteness(StrEnum):
    PARTIAL = "partial"
    COMPLETE = "complete"


class PsalmLearningStatus(StrEnum):
    NOT_STARTED = "not_started"
    LEARNING_SECTIONS = "learning_sections"
    CONSOLIDATING = "consolidating"
    LEARNED = "learned"


@dataclass(frozen=True, slots=True)
class PsalmVerse:
    verse_number: int
    canonical_text: str

    def __post_init__(self) -> None:
        if self.verse_number <= 0:
            raise InvariantViolationError("Verse number must be positive")
        if not self.canonical_text.strip():
            raise InvariantViolationError("Verse text must not be blank")


@dataclass(frozen=True, slots=True)
class Psalm:
    id: str
    translation_id: str
    psalm_number: int
    canonical_text: str
    verse_count: int
    completeness: PsalmCompleteness
    verses: tuple[PsalmVerse, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvariantViolationError("Psalm ID must not be blank")
        if not self.translation_id.strip():
            raise InvariantViolationError("Translation ID must not be blank")
        if self.psalm_number <= 0:
            raise InvariantViolationError("Psalm number must be positive")
        if not self.canonical_text.strip():
            raise InvariantViolationError("Canonical text must not be blank")
        if self.verse_count <= 0:
            raise InvariantViolationError("Verse count must be positive")
        if self.verses:
            numbers = [verse.verse_number for verse in self.verses]
            if numbers != sorted(numbers):
                raise InvariantViolationError("Psalm verses must be ordered")
            if len(set(numbers)) != len(numbers):
                raise InvariantViolationError("Psalm verses must be unique")
            if self.completeness is PsalmCompleteness.COMPLETE and numbers != list(
                range(1, len(self.verses) + 1)
            ):
                raise InvariantViolationError("Complete Psalms must contain verses 1..N")
            derived = "\n".join(verse.canonical_text for verse in self.verses).strip()
            if derived != self.canonical_text.strip():
                raise InvariantViolationError("Canonical text must match stored verses")
            if self.verse_count != len(self.verses):
                raise InvariantViolationError("Verse count must match stored verses")


@dataclass(frozen=True, slots=True)
class PsalmLearningPlan:
    psalm_id: str
    status: PsalmLearningStatus
    active_passage_id: str | None
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    version: int = 0

    def __post_init__(self) -> None:
        if not self.psalm_id.strip():
            raise InvariantViolationError("Psalm ID must not be blank")
        if self.version < 0:
            raise InvariantViolationError("Plan version must be non-negative")
        if self.status is PsalmLearningStatus.LEARNED and self.completed_at is None:
            raise InvariantViolationError("Learned plans must have completed_at")
        if self.status is not PsalmLearningStatus.LEARNED and self.completed_at is not None:
            raise InvariantViolationError("Only learned plans can have completed_at")

    def activate_passage(
        self,
        active_passage_id: str | None,
        when: datetime,
    ) -> PsalmLearningPlan:
        if self.status is PsalmLearningStatus.LEARNED:
            raise InvalidTransitionError("Learned plans cannot regress")
        return replace(
            self,
            status=PsalmLearningStatus.LEARNING_SECTIONS,
            active_passage_id=active_passage_id,
            updated_at=when,
            version=self.version + 1,
        )

    def begin_consolidation(
        self,
        active_passage_id: str | None,
        when: datetime,
    ) -> PsalmLearningPlan:
        if self.status is PsalmLearningStatus.LEARNED:
            raise InvalidTransitionError("Learned plans cannot regress")
        return replace(
            self,
            status=PsalmLearningStatus.CONSOLIDATING,
            active_passage_id=active_passage_id,
            updated_at=when,
            version=self.version + 1,
        )

    def mark_learned(self, when: datetime) -> PsalmLearningPlan:
        if self.status is PsalmLearningStatus.LEARNED:
            return self
        return replace(
            self,
            status=PsalmLearningStatus.LEARNED,
            active_passage_id=None,
            updated_at=when,
            completed_at=when,
            version=self.version + 1,
        )
