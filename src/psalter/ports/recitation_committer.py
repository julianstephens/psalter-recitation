from __future__ import annotations

from typing import Protocol

from psalter.domain.learning import LearningSession
from psalter.domain.recitation import RecitationAttempt
from psalter.domain.review import ReviewState


class RecitationCommitter(Protocol):
    def commit_assessment(
        self,
        attempt: RecitationAttempt,
        session: LearningSession,
        review_state: ReviewState | None,
    ) -> None: ...
