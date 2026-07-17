from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RecitationResult(StrEnum):
    PASS = "pass"
    RETRY = "retry"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True, slots=True)
class RecitationAttempt:
    id: str
    passage_id: str
    attempted_at: datetime
    transcript: str
    normalized_transcript: str
    result: RecitationResult
    accuracy: float
