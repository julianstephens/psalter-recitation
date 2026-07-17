import shutil
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
from psalter.application.errors import PersistenceConflictError
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

    with pytest.raises(PersistenceConflictError):
        committer.commit_assessment(attempt=bad_attempt, session=session, review_state=review_state)

    assert attempts.count_all() == 0
    assert sessions.get_by_passage(passage.id) is not None


def test_recitation_commit_detects_stale_session_and_prevents_lost_update(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    SqliteMigrator(db, migrations_dir()).apply_pending()
    passages = SqlitePassageRepository(db)
    sessions = SqliteLearningSessionRepository(db)
    attempts = SqliteRecitationRepository(db)
    committer = SqliteRecitationCommitter(db)

    passage = Passage(
        id="esv-psalm-3-1-1",
        translation_id="esv",
        psalm_number=3,
        start_verse=1,
        end_verse=1,
        canonical_text="LORD, how are they increased that trouble me",
    )
    passages.add(passage)
    base_time = datetime.now(UTC)
    base_session = LearningSession(
        id="s3",
        passage_id=passage.id,
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=4,
        successful_blank_recitations=0,
        started_at=base_time,
        updated_at=base_time,
        completed_at=None,
    )
    sessions.upsert(base_session)

    first_updated = base_session.record_successful_recitation(required_passes=2, when=base_time)
    second_updated = base_session.record_successful_recitation(required_passes=2, when=base_time)

    first_attempt = RecitationAttempt(
        id="a3",
        passage_id=passage.id,
        learning_session_id=base_session.id,
        source=RecitationSource.TYPED,
        submitted_text=passage.canonical_text,
        normalized_text="lord how are they increased that trouble me",
        attempted_at=base_time,
        result=RecitationResult.PASS,
        weighted_accuracy=1.0,
        assessment_policy_version="typed-v1",
        omission_count=0,
        substitution_count=0,
        insertion_count=0,
        longest_omitted_span=0,
        alignment_diagnostics=(),
    )
    second_attempt = RecitationAttempt(
        id="a4",
        passage_id=passage.id,
        learning_session_id=base_session.id,
        source=RecitationSource.TYPED,
        submitted_text=passage.canonical_text,
        normalized_text="lord how are they increased that trouble me",
        attempted_at=base_time,
        result=RecitationResult.PASS,
        weighted_accuracy=1.0,
        assessment_policy_version="typed-v1",
        omission_count=0,
        substitution_count=0,
        insertion_count=0,
        longest_omitted_span=0,
        alignment_diagnostics=(),
    )

    committer.commit_assessment(attempt=first_attempt, session=first_updated, review_state=None)
    with pytest.raises(PersistenceConflictError):
        committer.commit_assessment(
            attempt=second_attempt, session=second_updated, review_state=None
        )

    latest = sessions.get_by_passage(passage.id)
    assert latest is not None
    assert latest.successful_blank_recitations == 1
    assert attempts.count_all() == 1


def test_migration_failure_rolls_back_schema_and_bookkeeping(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    custom_migrations = tmp_path / "migrations"
    custom_migrations.mkdir()
    shutil.copy(migrations_dir() / "001_initial.sql", custom_migrations / "001_initial.sql")
    migrator = SqliteMigrator(db, custom_migrations)
    assert migrator.apply_pending() == ["001_initial.sql"]

    with db.open_connection() as conn, conn:
        conn.execute(
            """
            INSERT INTO passages(
                id, translation_id, psalm_number, start_verse, end_verse, canonical_text
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("p1", "esv", 1, 1, 1, "Blessed is the man"),
        )

    (custom_migrations / "002_failure_injection.sql").write_text(
        """
CREATE TABLE passages_new (
    id TEXT PRIMARY KEY,
    translation_id TEXT NOT NULL,
    psalm_number INTEGER NOT NULL,
    start_verse INTEGER NOT NULL,
    end_verse INTEGER NOT NULL,
    canonical_text TEXT NOT NULL
);
INSERT INTO passages_new SELECT * FROM passages;
DROP TABLE passages;
ALTER TABLE passages_new RENAME TO passages;
INSERT INTO missing_table(x) VALUES (1);
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(sqlite3.OperationalError):
        migrator.apply_pending()

    with db.open_connection() as conn:
        row = conn.execute("SELECT canonical_text FROM passages WHERE id = 'p1'").fetchone()
        versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert row is not None
    assert row["canonical_text"] == "Blessed is the man"
    assert [str(item["version"]) for item in versions] == ["001_initial.sql"]


def test_migration_rejects_legacy_orphan_attempts_without_sessions(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    staged_migrations = tmp_path / "staged-migrations"
    staged_migrations.mkdir()
    shutil.copy(migrations_dir() / "001_initial.sql", staged_migrations / "001_initial.sql")
    migrator = SqliteMigrator(db, staged_migrations)
    assert migrator.apply_pending() == ["001_initial.sql"]

    with db.open_connection() as conn, conn:
        conn.execute(
            """
            INSERT INTO passages(
                id, translation_id, psalm_number, start_verse, end_verse, canonical_text
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("p2", "esv", 2, 1, 1, "Why do the heathen rage"),
        )
        conn.execute(
            """
            INSERT INTO recitation_attempts(
                id, passage_id, attempted_at, transcript, normalized_transcript, result, accuracy
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-a1",
                "p2",
                datetime.now(UTC).isoformat(),
                "Why do the heathen rage",
                "why do the heathen rage",
                "pass",
                1.0,
            ),
        )

    shutil.copy(
        migrations_dir() / "002_learning_vertical_slice.sql",
        staged_migrations / "002_learning_vertical_slice.sql",
    )
    with pytest.raises(sqlite3.IntegrityError):
        migrator.apply_pending()

    with db.open_connection() as conn:
        versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        legacy_attempt_count = conn.execute(
            "SELECT COUNT(*) AS n FROM recitation_attempts"
        ).fetchone()
        learning_columns = conn.execute("PRAGMA table_info(learning_sessions)").fetchall()

    assert [str(item["version"]) for item in versions] == ["001_initial.sql"]
    assert legacy_attempt_count is not None
    assert int(legacy_attempt_count["n"]) == 1
    assert "updated_at" not in {str(item["name"]) for item in learning_columns}
