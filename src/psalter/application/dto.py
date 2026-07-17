from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from psalter.domain.learning import LearningPhase
from psalter.domain.recitation import AlignmentKind, RecitationResult, RecitationSource


@dataclass(frozen=True, slots=True)
class AudioRecordingRequest:
    passage_id: str
    sample_rate_hz: int
    channels: int
    wait_for_stop: Callable[[], None] | None = None


@dataclass(frozen=True, slots=True)
class AudioArtifact:
    path: Path
    sample_rate_hz: int
    channels: int
    duration_seconds: float | None


@dataclass(frozen=True, slots=True)
class TranscriptArtifact:
    text: str
    provider: str
    model: str
    raw_output_path: Path | None


@dataclass(frozen=True, slots=True)
class LearningSessionDTO:
    id: str
    passage_id: str
    phase: LearningPhase
    practice_level: int
    successful_blank_recitations: int
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PassageSummaryDTO:
    id: str
    translation_id: str
    psalm_number: int
    start_verse: int
    end_verse: int


@dataclass(frozen=True, slots=True)
class PassageDetailDTO:
    id: str
    translation_id: str
    psalm_number: int
    start_verse: int
    end_verse: int
    canonical_text: str


@dataclass(frozen=True, slots=True)
class LearningViewDTO:
    passage: PassageDetailDTO
    session: LearningSessionDTO


@dataclass(frozen=True, slots=True)
class PracticeViewDTO:
    session: LearningSessionDTO
    masked_text: str
    level: int
    max_level: int


@dataclass(frozen=True, slots=True)
class AlignmentIssueDTO:
    kind: AlignmentKind
    expected_token: str | None
    submitted_token: str | None


@dataclass(frozen=True, slots=True)
class RecitationAssessmentDTO:
    attempt_id: str
    passage_id: str
    learning_session_id: str
    source: RecitationSource
    result: RecitationResult
    weighted_accuracy: float
    omission_count: int
    substitution_count: int
    insertion_count: int
    longest_omitted_span: int
    policy_version: str
    failure_reasons: tuple[str, ...]
    omissions: tuple[str, ...]
    substitutions: tuple[tuple[str, str], ...]
    insertions: tuple[str, ...]
    remaining_successes_required: int
    issues: tuple[AlignmentIssueDTO, ...]


@dataclass(frozen=True, slots=True)
class DueReviewDTO:
    passage_id: str
    station: int
    next_review_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProgressSummaryDTO:
    total_passages: int
    unseen_passages: int
    exposure_passages: int
    practice_passages: int
    ready_passages: int
    reinforcement_passages: int
    learned_passages: int
    reviews_due: int
    total_recitation_attempts: int
    successful_recitation_attempts: int


@dataclass(frozen=True, slots=True)
class RecitationSubmission:
    passage_id: str
    source: RecitationSource
    text: str
