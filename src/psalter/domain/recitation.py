from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RecitationResult(StrEnum):
    PASS = "pass"
    RETRY = "retry"
    MANUAL_REVIEW = "manual_review"


class RecitationSource(StrEnum):
    TYPED = "typed"
    SPEECH_TRANSCRIPT = "speech_transcript"


class AlignmentKind(StrEnum):
    MATCH = "match"
    SUBSTITUTION = "substitution"
    OMISSION = "omission"
    INSERTION = "insertion"


@dataclass(frozen=True, slots=True)
class AlignmentOperation:
    kind: AlignmentKind
    expected_token: str | None
    submitted_token: str | None
    expected_index: int | None
    submitted_index: int | None


@dataclass(frozen=True, slots=True)
class RecitationAttempt:
    id: str
    passage_id: str
    learning_session_id: str
    source: RecitationSource
    submitted_text: str
    normalized_text: str
    attempted_at: datetime
    result: RecitationResult
    weighted_accuracy: float
    assessment_policy_version: str
    omission_count: int
    substitution_count: int
    insertion_count: int
    longest_omitted_span: int
    alignment_diagnostics: tuple[AlignmentOperation, ...]
