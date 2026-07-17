from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from psalter.domain.learning import LearningPhase, LearningSession
from psalter.domain.passage import Passage
from psalter.domain.recitation import RecitationAttempt
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

            pending: list[Path] = []
            for path in sorted(self._migrations_dir.glob("*.sql")):
                if path.name not in applied:
                    pending.append(path)

            applied_now: list[str] = []
            for migration in pending:
                sql = migration.read_text(encoding="utf-8")
                with conn:
                    conn.executescript(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                        (migration.name, datetime.now(UTC).isoformat()),
                    )
                applied_now.append(migration.name)

            return applied_now


class SqlitePassageRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

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

    def count_all(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM passages").fetchone()
        return int(row["n"]) if row is not None else 0


class SqliteLearningSessionRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def get_latest_by_passage(self, passage_id: str) -> LearningSession | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, passage_id, phase, practice_level, successful_blank_recitations,
                       started_at, completed_at
                FROM learning_sessions
                WHERE passage_id = ?
                ORDER BY started_at DESC
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
            completed_at=_str_to_dt(row["completed_at"]),
        )

    def upsert(self, session: LearningSession) -> None:
        with self._db.open_connection() as conn:
            conn.execute(
                """
                INSERT INTO learning_sessions(
                    id, passage_id, phase, practice_level,
                    successful_blank_recitations, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    passage_id = excluded.passage_id,
                    phase = excluded.phase,
                    practice_level = excluded.practice_level,
                    successful_blank_recitations = excluded.successful_blank_recitations,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at
                """,
                (
                    session.id,
                    session.passage_id,
                    session.phase.value,
                    session.practice_level,
                    session.successful_blank_recitations,
                    _dt_to_str(session.started_at),
                    _dt_to_str(session.completed_at),
                ),
            )

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
        with self._db.open_connection() as conn:
            conn.execute(
                """
                INSERT INTO recitation_attempts(
                    id, passage_id, attempted_at, transcript,
                    normalized_transcript, result, accuracy
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.id,
                    attempt.passage_id,
                    _dt_to_str(attempt.attempted_at),
                    attempt.transcript,
                    attempt.normalized_transcript,
                    attempt.result.value,
                    attempt.accuracy,
                ),
            )


class SqliteReviewRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def list_due(self, now: datetime) -> list[ReviewState]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT passage_id, station, learned_at, next_review_at, status
                FROM review_states
                WHERE next_review_at IS NOT NULL
                  AND next_review_at <= ?
                ORDER BY next_review_at ASC
                """,
                (_dt_to_str(now),),
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
