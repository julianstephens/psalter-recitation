from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from psalter.application.errors import PassageAlreadyExistsError, PersistenceConflictError
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


def _dt_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _str_to_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _serialize_alignment(ops: tuple[AlignmentOperation, ...]) -> str:
    return json.dumps(
        [
            {
                "kind": item.kind.value,
                "expected_token": item.expected_token,
                "submitted_token": item.submitted_token,
                "expected_index": item.expected_index,
                "submitted_index": item.submitted_index,
            }
            for item in ops
        ],
        separators=(",", ":"),
    )


def _deserialize_alignment(raw_json: str) -> tuple[AlignmentOperation, ...]:
    parsed = json.loads(raw_json)
    if not isinstance(parsed, list):
        raise ValueError("Alignment diagnostics must be a list")
    return tuple(
        AlignmentOperation(
            kind=AlignmentKind(str(item["kind"])),
            expected_token=item.get("expected_token"),
            submitted_token=item.get("submitted_token"),
            expected_index=item.get("expected_index"),
            submitted_index=item.get("submitted_index"),
        )
        for item in parsed
    )


def _quote_sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True, slots=True)
class SqliteDatabase:
    path: Path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def open_connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()


class SqliteMigrator:
    def __init__(self, database: SqliteDatabase, migrations_dir: Path) -> None:
        self._db = database
        self._migrations_dir = migrations_dir

    def apply_pending(self) -> list[str]:
        self._db.initialize()
        with self._db.open_connection() as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
            applied = {str(row["version"]) for row in rows}
            pending = [
                path
                for path in sorted(self._migrations_dir.glob("*.sql"))
                if path.name not in applied
            ]

            applied_now: list[str] = []
            for migration in pending:
                sql = migration.read_text(encoding="utf-8")
                applied_at = datetime.now(UTC).isoformat()
                wrapped_sql = (
                    "BEGIN IMMEDIATE;\n"
                    f"{sql}\n"
                    "INSERT INTO schema_migrations(version, applied_at) VALUES ("
                    f"{_quote_sql_text(migration.name)}, {_quote_sql_text(applied_at)}"
                    ");\n"
                    "COMMIT;\n"
                )
                try:
                    conn.executescript(wrapped_sql)
                except sqlite3.Error:
                    conn.rollback()
                    raise
                applied_now.append(migration.name)
            return applied_now


class SqlitePassageRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def add(self, passage: Passage) -> None:
        try:
            with self._db.open_connection() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO passages(
                        id, translation_id, psalm_number, start_verse, end_verse, canonical_text
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        passage.id,
                        passage.translation_id,
                        passage.psalm_number,
                        passage.start_verse,
                        passage.end_verse,
                        passage.canonical_text,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise PassageAlreadyExistsError(f"Passage already exists: {passage.id}") from exc

    def get_by_id(self, passage_id: str) -> Passage | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, translation_id, psalm_number, start_verse, end_verse, canonical_text
                FROM passages
                WHERE id = ?
                """,
                (passage_id,),
            ).fetchone()
        if row is None:
            return None
        return Passage(
            id=str(row["id"]),
            translation_id=str(row["translation_id"]),
            psalm_number=int(row["psalm_number"]),
            start_verse=int(row["start_verse"]),
            end_verse=int(row["end_verse"]),
            canonical_text=str(row["canonical_text"]),
        )

    def list_all(self) -> list[Passage]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, translation_id, psalm_number, start_verse, end_verse, canonical_text
                FROM passages
                ORDER BY psalm_number, start_verse, end_verse, id
                """
            ).fetchall()
        return [
            Passage(
                id=str(row["id"]),
                translation_id=str(row["translation_id"]),
                psalm_number=int(row["psalm_number"]),
                start_verse=int(row["start_verse"]),
                end_verse=int(row["end_verse"]),
                canonical_text=str(row["canonical_text"]),
            )
            for row in rows
        ]

    def count_all(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM passages").fetchone()
        return int(row["n"]) if row is not None else 0


class SqliteLearningSessionRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def get_by_passage(self, passage_id: str) -> LearningSession | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, passage_id, phase, practice_level, successful_blank_recitations,
                       started_at, updated_at, completed_at
                FROM learning_sessions
                WHERE passage_id = ?
                LIMIT 1
                """,
                (passage_id,),
            ).fetchone()
        if row is None:
            return None
        return LearningSession(
            id=str(row["id"]),
            passage_id=str(row["passage_id"]),
            phase=LearningPhase(str(row["phase"])),
            practice_level=int(row["practice_level"]),
            successful_blank_recitations=int(row["successful_blank_recitations"]),
            started_at=_str_to_dt(str(row["started_at"])) or datetime.now(UTC),
            updated_at=_str_to_dt(str(row["updated_at"])) or datetime.now(UTC),
            completed_at=_str_to_dt(row["completed_at"]),
        )

    def upsert(self, session: LearningSession) -> None:
        with self._db.open_connection() as conn, conn:
            conn.execute(
                """
                INSERT INTO learning_sessions(
                    id, passage_id, phase, practice_level, successful_blank_recitations,
                    started_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    passage_id = excluded.passage_id,
                    phase = excluded.phase,
                    practice_level = excluded.practice_level,
                    successful_blank_recitations = excluded.successful_blank_recitations,
                    started_at = excluded.started_at,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at
                """,
                (
                    session.id,
                    session.passage_id,
                    session.phase.value,
                    session.practice_level,
                    session.successful_blank_recitations,
                    _dt_to_str(session.started_at),
                    _dt_to_str(session.updated_at),
                    _dt_to_str(session.completed_at),
                ),
            )

    def count_all(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM learning_sessions").fetchone()
        return int(row["n"]) if row is not None else 0

    def count_by_phase(self, phase: LearningPhase) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM learning_sessions WHERE phase = ?",
                (phase.value,),
            ).fetchone()
        return int(row["n"]) if row is not None else 0


class SqliteRecitationRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def add(self, attempt: RecitationAttempt) -> None:
        with self._db.open_connection() as conn, conn:
            conn.execute(
                """
                INSERT INTO recitation_attempts(
                    id, passage_id, learning_session_id, source, submitted_text,
                    normalized_text, attempted_at, result, weighted_accuracy,
                    assessment_policy_version, omission_count, substitution_count,
                    insertion_count, longest_omitted_span, alignment_diagnostics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.id,
                    attempt.passage_id,
                    attempt.learning_session_id,
                    attempt.source.value,
                    attempt.submitted_text,
                    attempt.normalized_text,
                    _dt_to_str(attempt.attempted_at),
                    attempt.result.value,
                    attempt.weighted_accuracy,
                    attempt.assessment_policy_version,
                    attempt.omission_count,
                    attempt.substitution_count,
                    attempt.insertion_count,
                    attempt.longest_omitted_span,
                    _serialize_alignment(attempt.alignment_diagnostics),
                ),
            )

    def count_all(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM recitation_attempts").fetchone()
        return int(row["n"]) if row is not None else 0

    def count_successful(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM recitation_attempts WHERE result = ?",
                (RecitationResult.PASS.value,),
            ).fetchone()
        return int(row["n"]) if row is not None else 0

    def get_latest(self, passage_id: str) -> RecitationAttempt | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, passage_id, learning_session_id, source, submitted_text, normalized_text,
                       attempted_at, result, weighted_accuracy, assessment_policy_version,
                       omission_count, substitution_count, insertion_count, longest_omitted_span,
                       alignment_diagnostics
                FROM recitation_attempts
                WHERE passage_id = ?
                ORDER BY attempted_at DESC
                LIMIT 1
                """,
                (passage_id,),
            ).fetchone()
        if row is None:
            return None
        return RecitationAttempt(
            id=str(row["id"]),
            passage_id=str(row["passage_id"]),
            learning_session_id=str(row["learning_session_id"]),
            source=RecitationSource(str(row["source"])),
            submitted_text=str(row["submitted_text"]),
            normalized_text=str(row["normalized_text"]),
            attempted_at=_str_to_dt(str(row["attempted_at"])) or datetime.now(UTC),
            result=RecitationResult(str(row["result"])),
            weighted_accuracy=float(row["weighted_accuracy"]),
            assessment_policy_version=str(row["assessment_policy_version"]),
            omission_count=int(row["omission_count"]),
            substitution_count=int(row["substitution_count"]),
            insertion_count=int(row["insertion_count"]),
            longest_omitted_span=int(row["longest_omitted_span"]),
            alignment_diagnostics=_deserialize_alignment(str(row["alignment_diagnostics"])),
        )


class SqliteReviewRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def get_by_passage(self, passage_id: str) -> ReviewState | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT passage_id, station, learned_at, next_review_at, status
                FROM review_states
                WHERE passage_id = ?
                LIMIT 1
                """,
                (passage_id,),
            ).fetchone()
        if row is None:
            return None
        return ReviewState(
            passage_id=str(row["passage_id"]),
            station=int(row["station"]),
            learned_at=_str_to_dt(row["learned_at"]),
            next_review_at=_str_to_dt(row["next_review_at"]),
            status=ReviewStatus(str(row["status"])),
        )

    def upsert(self, state: ReviewState) -> None:
        with self._db.open_connection() as conn, conn:
            conn.execute(
                """
                INSERT INTO review_states(
                    passage_id, station, learned_at, next_review_at, status
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(passage_id) DO UPDATE SET
                    station = excluded.station,
                    learned_at = excluded.learned_at,
                    next_review_at = excluded.next_review_at,
                    status = excluded.status
                """,
                (
                    state.passage_id,
                    state.station,
                    _dt_to_str(state.learned_at),
                    _dt_to_str(state.next_review_at),
                    state.status.value,
                ),
            )

    def list_due(self, now: datetime) -> list[ReviewState]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT passage_id, station, learned_at, next_review_at, status
                FROM review_states
                WHERE status = ?
                  AND next_review_at IS NOT NULL
                  AND next_review_at <= ?
                ORDER BY next_review_at ASC
                """,
                (ReviewStatus.ACTIVE.value, _dt_to_str(now)),
            ).fetchall()
        return [
            ReviewState(
                passage_id=str(row["passage_id"]),
                station=int(row["station"]),
                learned_at=_str_to_dt(row["learned_at"]),
                next_review_at=_str_to_dt(row["next_review_at"]),
                status=ReviewStatus(str(row["status"])),
            )
            for row in rows
        ]


class SqliteRecitationCommitter:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def commit_assessment(
        self,
        attempt: RecitationAttempt,
        session: LearningSession,
        review_state: ReviewState | None,
    ) -> None:
        with self._db.open_connection() as conn, conn:
            expected_successes = _expected_success_count_before_attempt(
                attempt=attempt, session=session
            )
            update_result = conn.execute(
                """
                UPDATE learning_sessions
                SET phase = ?, practice_level = ?, successful_blank_recitations = ?,
                    started_at = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
                  AND phase = ?
                  AND successful_blank_recitations = ?
                """,
                (
                    session.phase.value,
                    session.practice_level,
                    session.successful_blank_recitations,
                    _dt_to_str(session.started_at),
                    _dt_to_str(session.updated_at),
                    _dt_to_str(session.completed_at),
                    session.id,
                    LearningPhase.READY_FOR_RECITATION.value,
                    expected_successes,
                ),
            )
            if update_result.rowcount != 1:
                raise PersistenceConflictError(
                    "Learning session changed during recitation commit; retry submission."
                )
            conn.execute(
                """
                INSERT INTO recitation_attempts(
                    id, passage_id, learning_session_id, source, submitted_text,
                    normalized_text, attempted_at, result, weighted_accuracy,
                    assessment_policy_version, omission_count, substitution_count,
                    insertion_count, longest_omitted_span, alignment_diagnostics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.id,
                    attempt.passage_id,
                    attempt.learning_session_id,
                    attempt.source.value,
                    attempt.submitted_text,
                    attempt.normalized_text,
                    _dt_to_str(attempt.attempted_at),
                    attempt.result.value,
                    attempt.weighted_accuracy,
                    attempt.assessment_policy_version,
                    attempt.omission_count,
                    attempt.substitution_count,
                    attempt.insertion_count,
                    attempt.longest_omitted_span,
                    _serialize_alignment(attempt.alignment_diagnostics),
                ),
            )
            if review_state is not None:
                conn.execute(
                    """
                    INSERT INTO review_states(
                        passage_id, station, learned_at, next_review_at, status
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(passage_id) DO UPDATE SET
                        station = excluded.station,
                        learned_at = excluded.learned_at,
                        next_review_at = excluded.next_review_at,
                        status = excluded.status
                    """,
                    (
                        review_state.passage_id,
                        review_state.station,
                        _dt_to_str(review_state.learned_at),
                        _dt_to_str(review_state.next_review_at),
                        review_state.status.value,
                    ),
                )


def _expected_success_count_before_attempt(
    attempt: RecitationAttempt, session: LearningSession
) -> int:
    if attempt.result is RecitationResult.PASS:
        return max(0, session.successful_blank_recitations - 1)
    return session.successful_blank_recitations
