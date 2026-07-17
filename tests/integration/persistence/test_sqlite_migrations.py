import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from psalter.adapters.persistence import (
    SqliteDatabase,
    SqliteLearningSessionRepository,
    SqliteMigrator,
    SqlitePassageRepository,
    SqliteRecitationCommitter,
    SqliteRecitationRepository,
    migrations_dir,
)
from psalter.domain.learning import LearningPhase, LearningSession
from psalter.domain.passage import Passage
from psalter.domain.recitation import (
    AlignmentKind,
    AlignmentOperation,
    RecitationAttempt,
    RecitationResult,
    RecitationSource,
)
from psalter.domain.review import ReviewState, ReviewStatus


def test_sqlite_migrations_are_idempotent(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    migrator = SqliteMigrator(db, migrations_dir())

    first = migrator.apply_pending()
    second = migrator.apply_pending()

    assert first == ["001_initial.sql", "002_learning_vertical_slice.sql"]
    assert second == []


def test_sqlite_foreign_keys_enabled(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    SqliteMigrator(db, migrations_dir()).apply_pending()

    with db.open_connection() as conn:
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()

    assert fk_status is not None
    assert int(fk_status[0]) == 1


def test_attempt_diagnostics_round_trip_and_session_foreign_key(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    SqliteMigrator(db, migrations_dir()).apply_pending()
    passages = SqlitePassageRepository(db)
    sessions = SqliteLearningSessionRepository(db)
    attempts = SqliteRecitationRepository(db)
    committer = SqliteRecitationCommitter(db)

    passage = Passage(
        id="esv-psalm-1-1-1",
        translation_id="esv",
        psalm_number=1,
        start_verse=1,
        end_verse=1,
        canonical_text="Blessed is the man",
    )
    passages.add(passage)
    session = LearningSession(
        id="s1",
        passage_id=passage.id,
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=4,
        successful_blank_recitations=0,
        started_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        completed_at=None,
    )
    sessions.upsert(session)
    attempt = RecitationAttempt(
        id="a1",
        passage_id=passage.id,
        learning_session_id=session.id,
        source=RecitationSource.TYPED,
        submitted_text="Blessed is the man",
        normalized_text="blessed is the man",
        attempted_at=datetime.now(UTC),
        result=RecitationResult.PASS,
        weighted_accuracy=1.0,
        assessment_policy_version="typed-v1",
        omission_count=0,
        substitution_count=0,
        insertion_count=0,
        longest_omitted_span=0,
        alignment_diagnostics=(
            AlignmentOperation(
                kind=AlignmentKind.MATCH,
                expected_token="blessed",
                submitted_token="blessed",
                expected_index=0,
                submitted_index=0,
            ),
        ),
    )
    committer.commit_assessment(attempt=attempt, session=session, review_state=None)
    latest = attempts.get_latest(passage.id)
    assert latest is not None
    assert latest.learning_session_id == session.id
    assert latest.assessment_policy_version == "typed-v1"


def test_atomic_commit_rolls_back_all_writes_on_failure(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    SqliteMigrator(db, migrations_dir()).apply_pending()
    passages = SqlitePassageRepository(db)
    sessions = SqliteLearningSessionRepository(db)
    attempts = SqliteRecitationRepository(db)
    committer = SqliteRecitationCommitter(db)

    passage = Passage(
        id="esv-psalm-2-1-1",
        translation_id="esv",
        psalm_number=2,
        start_verse=1,
        end_verse=1,
        canonical_text="Why do the nations rage",
    )
    passages.add(passage)
    session = LearningSession(
        id="s2",
        passage_id=passage.id,
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=4,
        successful_blank_recitations=1,
        started_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        completed_at=None,
    )
    sessions.upsert(session)
    bad_attempt = RecitationAttempt(
        id="a2",
        passage_id=passage.id,
        learning_session_id="missing-session",
        source=RecitationSource.TYPED,
        submitted_text="Why do the nations rage",
        normalized_text="why do the nations rage",
        attempted_at=datetime.now(UTC),
        result=RecitationResult.PASS,
        weighted_accuracy=1.0,
        assessment_policy_version="typed-v1",
        omission_count=0,
        substitution_count=0,
        insertion_count=0,
        longest_omitted_span=0,
        alignment_diagnostics=(),
    )
    review_state = ReviewState(
        passage_id=passage.id,
        station=1,
        learned_at=datetime.now(UTC),
        next_review_at=datetime.now(UTC),
        status=ReviewStatus.ACTIVE,
    )

    with pytest.raises(sqlite3.IntegrityError):
        committer.commit_assessment(attempt=bad_attempt, session=session, review_state=review_state)

    assert attempts.count_all() == 0
    assert sessions.get_by_passage(passage.id) is not None
