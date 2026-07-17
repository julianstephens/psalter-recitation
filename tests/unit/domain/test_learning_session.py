from datetime import UTC, datetime

import pytest

from psalter.domain.errors import InvalidTransitionError
from psalter.domain.learning import LearningPhase, LearningSession


def _session(phase: LearningPhase) -> LearningSession:
    return LearningSession(
        id="s1",
        passage_id="p1",
        phase=phase,
        practice_level=0,
        successful_blank_recitations=0,
        started_at=datetime.now(UTC),
        completed_at=None,
    )


def test_valid_learning_session_transitions() -> None:
    session = _session(LearningPhase.UNSEEN)
    session = session.begin_exposure()
    assert session.phase is LearningPhase.EXPOSURE
    session = session.complete_exposure()
    assert session.phase is LearningPhase.PRACTICE
    session = session.mark_practice_ready()
    assert session.phase is LearningPhase.READY_FOR_RECITATION
    session = session.mark_needs_reinforcement()
    assert session.phase is LearningPhase.NEEDS_REINFORCEMENT
    session = session.resume_practice()
    assert session.phase is LearningPhase.PRACTICE


def test_invalid_learning_session_transition_raises() -> None:
    session = _session(LearningPhase.EXPOSURE)
    with pytest.raises(InvalidTransitionError):
        session.mark_practice_ready()
