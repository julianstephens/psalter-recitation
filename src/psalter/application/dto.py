from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psalter.domain.learning import LearningPhase


@dataclass(frozen=True, slots=True)
class AudioArtifact:
    uri: str


@dataclass(frozen=True, slots=True)
class TranscriptDTO:
    transcript: str
    normalized_transcript: str


@dataclass(frozen=True, slots=True)
class LearningSessionDTO:
    id: str
    passage_id: str
    phase: LearningPhase
    practice_level: int
    successful_blank_recitations: int
    started_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PassageDTO:
    id: str
    translation_id: str
    psalm_number: int
    start_verse: int
    end_verse: int


@dataclass(frozen=True, slots=True)
class DueReviewDTO:
    passage_id: str
    station: int
    next_review_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProgressSummaryDTO:
    total_passages: int
    passages_currently_learning: int
    passages_learned: int
    reviews_due: int
