from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from psalter.application.errors import (
    PassageAlreadyExistsError,
    PersistenceConflictError,
    PsalmAlreadyExistsError,
)
from psalter.domain.learning import LearningPhase, LearningSession
from psalter.domain.passage import Passage, PassageKind
from psalter.domain.psalm import (
    Psalm,
    PsalmCompleteness,
    PsalmLearningPlan,
    PsalmLearningStatus,
    PsalmVerse,
)
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


class SqlitePsalmRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def add_psalm_bundle(self, psalm: Psalm, passages: tuple[Passage, ...]) -> None:
        try:
            with self._db.open_connection() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO psalms(
                        id, translation_id, psalm_number, canonical_text, verse_count, completeness
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        psalm.id,
                        psalm.translation_id,
                        psalm.psalm_number,
                        psalm.canonical_text,
                        psalm.verse_count,
                        psalm.completeness.value,
                    ),
                )
                conn.executemany(
                    """
                    INSERT INTO psalm_verses(psalm_id, verse_number, canonical_text)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (psalm.id, verse.verse_number, verse.canonical_text)
                        for verse in psalm.verses
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO passages(
                        id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                        canonical_text, sequence_number, kind, segmentation_policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            passage.id,
                            passage.psalm_id,
                            passage.translation_id,
                            passage.psalm_number,
                            passage.start_verse,
                            passage.end_verse,
                            passage.canonical_text,
                            passage.sequence_number,
                            passage.kind.value,
                            passage.segmentation_policy_version,
                        )
                        for passage in passages
                    ],
                )
        except sqlite3.IntegrityError as exc:
            if "psalms.translation_id, psalms.psalm_number" in str(exc) or "psalms.id" in str(exc):
                raise PsalmAlreadyExistsError(
                    f"Psalm already exists: {psalm.translation_id} Psalm {psalm.psalm_number}"
                ) from exc
            raise PassageAlreadyExistsError(
                "Generated Psalm passages conflict with existing data"
            ) from exc

    def get_by_id(self, psalm_id: str) -> Psalm | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, translation_id, psalm_number, canonical_text, verse_count, completeness
                FROM psalms
                WHERE id = ?
                """,
                (psalm_id,),
            ).fetchone()
            if row is None:
                return None
            verses = self._load_verses(conn, psalm_id)
        return _row_to_psalm(row, verses)

    def get_by_translation_and_number(self, translation_id: str, psalm_number: int) -> Psalm | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, translation_id, psalm_number, canonical_text, verse_count, completeness
                FROM psalms
                WHERE translation_id = ? AND psalm_number = ?
                LIMIT 1
                """,
                (translation_id, psalm_number),
            ).fetchone()
            if row is None:
                return None
            verses = self._load_verses(conn, str(row["id"]))
        return _row_to_psalm(row, verses)

    def list_by_number(self, psalm_number: int) -> list[Psalm]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, translation_id, psalm_number, canonical_text, verse_count, completeness
                FROM psalms
                WHERE psalm_number = ?
                ORDER BY translation_id ASC
                """,
                (psalm_number,),
            ).fetchall()
            psalm_ids = [str(row["id"]) for row in rows]
            verse_map = self._load_verses_for_psalms(conn, tuple(psalm_ids))
        return [_row_to_psalm(row, verse_map.get(str(row["id"]), ())) for row in rows]

    def list_all(self) -> list[Psalm]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, translation_id, psalm_number, canonical_text, verse_count, completeness
                FROM psalms
                ORDER BY psalm_number ASC, translation_id ASC
                """
            ).fetchall()
            psalm_ids = [str(row["id"]) for row in rows]
            verse_map = self._load_verses_for_psalms(conn, tuple(psalm_ids))
        return [_row_to_psalm(row, verse_map.get(str(row["id"]), ())) for row in rows]

    def _load_verses(self, conn: sqlite3.Connection, psalm_id: str) -> tuple[PsalmVerse, ...]:
        rows = conn.execute(
            """
            SELECT verse_number, canonical_text
            FROM psalm_verses
            WHERE psalm_id = ?
            ORDER BY verse_number ASC
            """,
            (psalm_id,),
        ).fetchall()
        return tuple(
            PsalmVerse(
                verse_number=int(row["verse_number"]),
                canonical_text=str(row["canonical_text"]),
            )
            for row in rows
        )

    def _load_verses_for_psalms(
        self,
        conn: sqlite3.Connection,
        psalm_ids: tuple[str, ...],
    ) -> dict[str, tuple[PsalmVerse, ...]]:
        if not psalm_ids:
            return {}
        placeholders = ", ".join("?" for _ in psalm_ids)
        rows = conn.execute(
            f"""
            SELECT psalm_id, verse_number, canonical_text
            FROM psalm_verses
            WHERE psalm_id IN ({placeholders})
            ORDER BY psalm_id ASC, verse_number ASC
            """,
            psalm_ids,
        ).fetchall()
        verse_map: dict[str, list[PsalmVerse]] = {psalm_id: [] for psalm_id in psalm_ids}
        for row in rows:
            verse_map[str(row["psalm_id"])].append(
                PsalmVerse(
                    verse_number=int(row["verse_number"]),
                    canonical_text=str(row["canonical_text"]),
                )
            )
        return {key: tuple(value) for key, value in verse_map.items()}


class SqlitePsalmLearningPlanRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def get_by_psalm_id(self, psalm_id: str) -> PsalmLearningPlan | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    psalm_id,
                    status,
                    active_passage_id,
                    started_at,
                    updated_at,
                    completed_at,
                    version
                FROM psalm_learning_plans
                WHERE psalm_id = ?
                LIMIT 1
                """,
                (psalm_id,),
            ).fetchone()
        if row is None:
            return None
        return PsalmLearningPlan(
            psalm_id=str(row["psalm_id"]),
            status=PsalmLearningStatus(str(row["status"])),
            active_passage_id=str(row["active_passage_id"]) if row["active_passage_id"] else None,
            started_at=_str_to_dt(str(row["started_at"])) or datetime.now(UTC),
            updated_at=_str_to_dt(str(row["updated_at"])) or datetime.now(UTC),
            completed_at=_str_to_dt(row["completed_at"]),
            version=int(row["version"]),
        )

    def upsert(self, plan: PsalmLearningPlan, expected_version: int | None = None) -> None:
        with self._db.open_connection() as conn, conn:
            if expected_version is None:
                conn.execute(
                    """
                    INSERT INTO psalm_learning_plans(
                        psalm_id,
                        status,
                        active_passage_id,
                        started_at,
                        updated_at,
                        completed_at,
                        version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(psalm_id) DO UPDATE SET
                        status = excluded.status,
                        active_passage_id = excluded.active_passage_id,
                        started_at = excluded.started_at,
                        updated_at = excluded.updated_at,
                        completed_at = excluded.completed_at,
                        version = excluded.version
                    """,
                    (
                        plan.psalm_id,
                        plan.status.value,
                        plan.active_passage_id,
                        _dt_to_str(plan.started_at),
                        _dt_to_str(plan.updated_at),
                        _dt_to_str(plan.completed_at),
                        plan.version,
                    ),
                )
                return

            result = conn.execute(
                """
                UPDATE psalm_learning_plans
                SET status = ?, active_passage_id = ?, started_at = ?, updated_at = ?,
                    completed_at = ?, version = ?
                WHERE psalm_id = ? AND version = ?
                """,
                (
                    plan.status.value,
                    plan.active_passage_id,
                    _dt_to_str(plan.started_at),
                    _dt_to_str(plan.updated_at),
                    _dt_to_str(plan.completed_at),
                    plan.version,
                    plan.psalm_id,
                    expected_version,
                ),
            )
            if result.rowcount == 1:
                return
            try:
                conn.execute(
                    """
                    INSERT INTO psalm_learning_plans(
                        psalm_id,
                        status,
                        active_passage_id,
                        started_at,
                        updated_at,
                        completed_at,
                        version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.psalm_id,
                        plan.status.value,
                        plan.active_passage_id,
                        _dt_to_str(plan.started_at),
                        _dt_to_str(plan.updated_at),
                        _dt_to_str(plan.completed_at),
                        plan.version,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise PersistenceConflictError(
                    "Psalm learning plan changed during update; retry the operation."
                ) from exc

    def list_all(self) -> list[PsalmLearningPlan]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    psalm_id,
                    status,
                    active_passage_id,
                    started_at,
                    updated_at,
                    completed_at,
                    version
                FROM psalm_learning_plans
                ORDER BY started_at ASC
                """
            ).fetchall()
        return [
            PsalmLearningPlan(
                psalm_id=str(row["psalm_id"]),
                status=PsalmLearningStatus(str(row["status"])),
                active_passage_id=(
                    str(row["active_passage_id"]) if row["active_passage_id"] else None
                ),
                started_at=_str_to_dt(str(row["started_at"])) or datetime.now(UTC),
                updated_at=_str_to_dt(str(row["updated_at"])) or datetime.now(UTC),
                completed_at=_str_to_dt(row["completed_at"]),
                version=int(row["version"]),
            )
            for row in rows
        ]


class SqlitePassageRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def add(self, passage: Passage) -> None:
        try:
            with self._db.open_connection() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO passages(
                        id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                        canonical_text, sequence_number, kind, segmentation_policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        passage.id,
                        passage.psalm_id,
                        passage.translation_id,
                        passage.psalm_number,
                        passage.start_verse,
                        passage.end_verse,
                        passage.canonical_text,
                        passage.sequence_number,
                        passage.kind.value,
                        passage.segmentation_policy_version,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise PassageAlreadyExistsError(f"Passage already exists: {passage.id}") from exc

    def get_by_id(self, passage_id: str) -> Passage | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                       canonical_text, sequence_number, kind, segmentation_policy_version
                FROM passages
                WHERE id = ?
                """,
                (passage_id,),
            ).fetchone()
        return _row_to_passage(row) if row is not None else None

    def list_all(self) -> list[Passage]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                       canonical_text, sequence_number, kind, segmentation_policy_version
                FROM passages
                ORDER BY psalm_number, translation_id, sequence_number, id
                """
            ).fetchall()
        return [_row_to_passage(row) for row in rows]

    def count_all(self) -> int:
        with self._db.open_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM passages WHERE kind = 'section'"
            ).fetchone()
        return int(row["n"]) if row is not None else 0

    def list_by_psalm(self, psalm_id: str, kind: PassageKind | None = None) -> list[Passage]:
        with self._db.open_connection() as conn:
            if kind is None:
                rows = conn.execute(
                    """
                    SELECT id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                           canonical_text, sequence_number, kind, segmentation_policy_version
                    FROM passages
                    WHERE psalm_id = ?
                    ORDER BY sequence_number ASC, id ASC
                    """,
                    (psalm_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                           canonical_text, sequence_number, kind, segmentation_policy_version
                    FROM passages
                    WHERE psalm_id = ? AND kind = ?
                    ORDER BY sequence_number ASC, id ASC
                    """,
                    (psalm_id, kind.value),
                ).fetchall()
        return [_row_to_passage(row) for row in rows]

    def get_consolidation_passage(self, psalm_id: str) -> Passage | None:
        with self._db.open_connection() as conn:
            row = conn.execute(
                """
                SELECT id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
                       canonical_text, sequence_number, kind, segmentation_policy_version
                FROM passages
                WHERE psalm_id = ? AND kind = ?
                LIMIT 1
                """,
                (psalm_id, PassageKind.CONSOLIDATION.value),
            ).fetchone()
        return _row_to_passage(row) if row is not None else None


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


def _row_to_psalm(row: sqlite3.Row, verses: tuple[PsalmVerse, ...]) -> Psalm:
    return Psalm(
        id=str(row["id"]),
        translation_id=str(row["translation_id"]),
        psalm_number=int(row["psalm_number"]),
        canonical_text=str(row["canonical_text"]),
        verse_count=int(row["verse_count"]),
        completeness=PsalmCompleteness(str(row["completeness"])),
        verses=verses,
    )


def _row_to_passage(row: sqlite3.Row) -> Passage:
    return Passage(
        id=str(row["id"]),
        psalm_id=str(row["psalm_id"]),
        translation_id=str(row["translation_id"]),
        psalm_number=int(row["psalm_number"]),
        start_verse=int(row["start_verse"]),
        end_verse=int(row["end_verse"]),
        canonical_text=str(row["canonical_text"]),
        sequence_number=int(row["sequence_number"]),
        kind=PassageKind(str(row["kind"])),
        segmentation_policy_version=(
            str(row["segmentation_policy_version"])
            if row["segmentation_policy_version"] is not None
            else None
        ),
    )


def _expected_success_count_before_attempt(
    attempt: RecitationAttempt,
    session: LearningSession,
) -> int:
    if attempt.result is RecitationResult.PASS:
        return max(0, session.successful_blank_recitations - 1)
    return session.successful_blank_recitations
