from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from psalter.application.dto import RecitationSubmission
from psalter.application.services.assessment import TypedTextAssessmentPolicy
from psalter.application.services.recitation import RecitationPolicy, RecitationService
from psalter.application.services.scheduling import InitialReviewSchedulingPolicy
from psalter.domain.learning import LearningPhase, LearningSession
from psalter.domain.passage import Passage
from psalter.domain.recitation import RecitationAttempt, RecitationResult, RecitationSource
from psalter.domain.review import ReviewState


@dataclass
class FakeClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


class FakePassages:
    def __init__(self, passage: Passage) -> None:
        self._passage = passage

    def add(self, passage: Passage) -> None:
        self._passage = passage

    def get_by_id(self, passage_id: str) -> Passage | None:
        return self._passage if self._passage.id == passage_id else None

    def list_all(self) -> list[Passage]:
        return [self._passage]

    def count_all(self) -> int:
        return 1


class FakeSessions:
    def __init__(self, session: LearningSession) -> None:
        self.session = session

    def get_by_passage(self, passage_id: str) -> LearningSession | None:
        return self.session if self.session.passage_id == passage_id else None

    def upsert(self, session: LearningSession) -> None:
        self.session = session

    def count_all(self) -> int:
        return 1

    def count_by_phase(self, phase: LearningPhase) -> int:
        return 1 if self.session.phase is phase else 0


class FakeReviews:
    def __init__(self) -> None:
        self.state: ReviewState | None = None

    def get_by_passage(self, passage_id: str) -> ReviewState | None:
        if self.state is not None and self.state.passage_id == passage_id:
            return self.state
        return None

    def upsert(self, state: ReviewState) -> None:
        self.state = state

    def list_due(self, now: datetime) -> list[ReviewState]:
        return []


class FakeCommitter:
    def __init__(self) -> None:
        self.attempts: list[RecitationAttempt] = []
        self.session: LearningSession | None = None
        self.review_state: ReviewState | None = None

    def commit_assessment(
        self,
        attempt: RecitationAttempt,
        session: LearningSession,
        review_state: ReviewState | None,
    ) -> None:
        self.attempts.append(attempt)
        self.session = session
        self.review_state = review_state


def _ready_session(successes: int = 0) -> LearningSession:
    return LearningSession(
        id="s1",
        passage_id="p1",
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=4,
        successful_blank_recitations=successes,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=None,
    )


def _passage() -> Passage:
    return Passage(
        id="p1",
        translation_id="esv",
        psalm_number=23,
        start_verse=1,
        end_verse=1,
        canonical_text="The LORD is my shepherd",
    )


def test_first_pass_keeps_session_ready() -> None:
    committer = FakeCommitter()
    service = RecitationService(
        passages=FakePassages(_passage()),
        sessions=FakeSessions(_ready_session(successes=0)),
        reviews=FakeReviews(),
        committer=committer,
        assessor=TypedTextAssessmentPolicy(),
        scheduling_policy=InitialReviewSchedulingPolicy(),
        policy=RecitationPolicy(required_passes_to_learn=2),
        clock=FakeClock(datetime(2026, 1, 2, tzinfo=UTC)),
    )

    assessment = service.submit_text(
        RecitationSubmission(
            passage_id="p1",
            source=RecitationSource.TYPED,
            text="the lord is my shepherd",
        )
    )
    assert assessment.result is RecitationResult.PASS
    assert assessment.remaining_successes_required == 1
    assert committer.session is not None
    assert committer.session.phase is LearningPhase.READY_FOR_RECITATION
    assert committer.session.successful_blank_recitations == 1


def test_second_pass_marks_learned_and_creates_review_state() -> None:
    committer = FakeCommitter()
    service = RecitationService(
        passages=FakePassages(_passage()),
        sessions=FakeSessions(_ready_session(successes=1)),
        reviews=FakeReviews(),
        committer=committer,
        assessor=TypedTextAssessmentPolicy(),
        scheduling_policy=InitialReviewSchedulingPolicy(),
        policy=RecitationPolicy(required_passes_to_learn=2),
        clock=FakeClock(datetime(2026, 1, 2, tzinfo=UTC)),
    )

    assessment = service.submit_text(
        RecitationSubmission(
            passage_id="p1",
            source=RecitationSource.TYPED,
            text="the lord is my shepherd",
        )
    )
    assert assessment.result is RecitationResult.PASS
    assert assessment.remaining_successes_required == 0
    assert committer.session is not None
    assert committer.session.phase is LearningPhase.LEARNED
    assert committer.review_state is not None


def test_failed_attempt_moves_to_reinforcement_without_losing_successes() -> None:
    committer = FakeCommitter()
    service = RecitationService(
        passages=FakePassages(_passage()),
        sessions=FakeSessions(_ready_session(successes=1)),
        reviews=FakeReviews(),
        committer=committer,
        assessor=TypedTextAssessmentPolicy(),
        scheduling_policy=InitialReviewSchedulingPolicy(),
        policy=RecitationPolicy(required_passes_to_learn=2),
        clock=FakeClock(datetime(2026, 1, 2, tzinfo=UTC)),
    )

    assessment = service.submit_text(
        RecitationSubmission(
            passage_id="p1",
            source=RecitationSource.TYPED,
            text="my shepherd",
        )
    )
    assert assessment.result is RecitationResult.RETRY
    assert committer.session is not None
    assert committer.session.phase is LearningPhase.NEEDS_REINFORCEMENT
    assert committer.session.successful_blank_recitations == 1
