from datetime import UTC, datetime, timedelta

import pytest

from psalter.domain.errors import InvalidTransitionError
from psalter.domain.learning import LearningPhase, LearningSession


def _session(phase: LearningPhase = LearningPhase.PRACTICE) -> LearningSession:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    completed_at = now if phase is LearningPhase.LEARNED else None
    return LearningSession(
        id="s1",
        passage_id="p1",
        phase=phase,
        practice_level=0,
        successful_blank_recitations=0,
        started_at=now,
        updated_at=now,
        completed_at=completed_at,
    )


def test_practice_level_progression_and_ready_transition() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    session = _session().advance_practice_level(max_level=5, when=now + timedelta(minutes=1))
    assert session.practice_level == 1
    assert session.phase is LearningPhase.PRACTICE

    ready_source = LearningSession(
        id="s1",
        passage_id="p1",
        phase=LearningPhase.PRACTICE,
        practice_level=4,
        successful_blank_recitations=0,
        started_at=now,
        updated_at=now,
        completed_at=None,
    )
    ready = ready_source.advance_practice_level(max_level=5, when=now + timedelta(minutes=2))
    assert ready.phase is LearningPhase.READY_FOR_RECITATION


def test_invalid_progression_outside_practice_raises() -> None:
    session = _session(LearningPhase.EXPOSURE)
    with pytest.raises(InvalidTransitionError):
        session.advance_practice_level(max_level=5, when=datetime(2026, 1, 2, tzinfo=UTC))


def test_two_pass_learning_and_retry_preserves_successes() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    ready = LearningSession(
        id="s1",
        passage_id="p1",
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=4,
        successful_blank_recitations=0,
        started_at=now,
        updated_at=now,
        completed_at=None,
    )
    first = ready.record_successful_recitation(required_passes=2, when=now + timedelta(minutes=1))
    assert first.phase is LearningPhase.READY_FOR_RECITATION
    assert first.successful_blank_recitations == 1

    failed = first.mark_needs_reinforcement(now + timedelta(minutes=2)).resume_practice(
        now + timedelta(minutes=3)
    )
    assert failed.successful_blank_recitations == 1

    back_ready = failed.mark_practice_ready(now + timedelta(minutes=4))
    second = back_ready.record_successful_recitation(
        required_passes=2, when=now + timedelta(minutes=5)
    )
    assert second.phase is LearningPhase.LEARNED
    assert second.successful_blank_recitations == 2
    assert second.completed_at == now + timedelta(minutes=5)


def test_learned_sessions_cannot_regress() -> None:
    learned = _session(LearningPhase.LEARNED)
    with pytest.raises(InvalidTransitionError):
        learned.resume_practice(datetime(2026, 1, 2, tzinfo=UTC))
