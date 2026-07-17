from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from psalter.adapters.persistence.sqlite import SqliteDatabase
from psalter.domain.installation import CatalogStatus, InstallationSettings
from psalter.domain.passage import Passage
from psalter.domain.psalm import Psalm


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


class SqliteInstallationSettingsRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def get_settings(self) -> InstallationSettings | None:
        try:
            with self._db.open_connection() as conn:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        scripture_provider,
                        default_translation_id,
                        default_translation_name,
                        catalog_status,
                        catalog_version,
                        initialized_at,
                        updated_at,
                        last_error
                    FROM installation_settings
                    WHERE id = 1
                    LIMIT 1
                    """
                ).fetchone()
        except sqlite3.OperationalError:
            return None
        if row is None:
            return None
        updated_at = _str_to_dt(str(row["updated_at"])) or datetime.now(UTC)
        return InstallationSettings(
            id=int(row["id"]),
            scripture_provider=str(row["scripture_provider"]),
            default_translation_id=(
                str(row["default_translation_id"]) if row["default_translation_id"] else None
            ),
            default_translation_name=(
                str(row["default_translation_name"]) if row["default_translation_name"] else None
            ),
            catalog_status=CatalogStatus(str(row["catalog_status"])),
            catalog_version=str(row["catalog_version"]) if row["catalog_version"] else None,
            initialized_at=_str_to_dt(row["initialized_at"]),
            updated_at=updated_at,
            last_error=str(row["last_error"]) if row["last_error"] else None,
        )

    def upsert(self, settings: InstallationSettings) -> None:
        with self._db.open_connection() as conn, conn:
            conn.execute(
                """
                INSERT INTO installation_settings(
                    id,
                    scripture_provider,
                    default_translation_id,
                    default_translation_name,
                    catalog_status,
                    catalog_version,
                    initialized_at,
                    updated_at,
                    last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    scripture_provider = excluded.scripture_provider,
                    default_translation_id = excluded.default_translation_id,
                    default_translation_name = excluded.default_translation_name,
                    catalog_status = excluded.catalog_status,
                    catalog_version = excluded.catalog_version,
                    initialized_at = excluded.initialized_at,
                    updated_at = excluded.updated_at,
                    last_error = excluded.last_error
                """,
                (
                    settings.id,
                    settings.scripture_provider,
                    settings.default_translation_id,
                    settings.default_translation_name,
                    settings.catalog_status.value,
                    settings.catalog_version,
                    _dt_to_str(settings.initialized_at),
                    _dt_to_str(settings.updated_at),
                    settings.last_error,
                ),
            )


class SqliteCatalogImportProgressRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def mark_pending(self, installation_id: int, psalm_number: int) -> None:
        self._upsert(
            installation_id=installation_id,
            psalm_number=psalm_number,
            status="pending",
            error=None,
            imported_at=None,
        )

    def mark_imported(self, installation_id: int, psalm_number: int) -> None:
        self._upsert(
            installation_id=installation_id,
            psalm_number=psalm_number,
            status="imported",
            error=None,
            imported_at=_dt_to_str(datetime.now(UTC)),
        )

    def mark_failed(self, installation_id: int, psalm_number: int, error: str) -> None:
        self._upsert(
            installation_id=installation_id,
            psalm_number=psalm_number,
            status="failed",
            error=error,
            imported_at=None,
        )

    def list_imported_psalm_numbers(self, installation_id: int) -> set[int]:
        with self._db.open_connection() as conn:
            rows = conn.execute(
                """
                SELECT psalm_number
                FROM catalog_import_progress
                WHERE installation_id = ? AND status = 'imported'
                """,
                (installation_id,),
            ).fetchall()
        return {int(row["psalm_number"]) for row in rows}

    def _upsert(
        self,
        *,
        installation_id: int,
        psalm_number: int,
        status: str,
        error: str | None,
        imported_at: str | None,
    ) -> None:
        with self._db.open_connection() as conn, conn:
            conn.execute(
                """
                INSERT INTO catalog_import_progress(
                    installation_id,
                    psalm_number,
                    status,
                    imported_at,
                    error
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(installation_id, psalm_number) DO UPDATE SET
                    status = excluded.status,
                    imported_at = excluded.imported_at,
                    error = excluded.error
                """,
                (
                    installation_id,
                    psalm_number,
                    status,
                    imported_at,
                    error,
                ),
            )


class SqlitePsalmCatalogCommitter:
    def __init__(self, database: SqliteDatabase) -> None:
        self._db = database

    def replace_psalm_bundle(
        self,
        *,
        installation_id: int,
        psalm: Psalm,
        passages: tuple[Passage, ...],
    ) -> None:
        with self._db.open_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM passages WHERE psalm_id = ?", (psalm.id,))
                conn.execute("DELETE FROM psalm_verses WHERE psalm_id = ?", (psalm.id,))
                conn.execute("DELETE FROM psalms WHERE id = ?", (psalm.id,))
                conn.execute(
                    """
                    INSERT INTO psalms(
                        id,
                        translation_id,
                        psalm_number,
                        canonical_text,
                        verse_count,
                        completeness
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
                conn.execute(
                    """
                    INSERT INTO catalog_import_progress(
                        installation_id,
                        psalm_number,
                        status,
                        imported_at,
                        error
                    ) VALUES (?, ?, 'imported', ?, NULL)
                    ON CONFLICT(installation_id, psalm_number) DO UPDATE SET
                        status = 'imported',
                        imported_at = excluded.imported_at,
                        error = NULL
                    """,
                    (
                        installation_id,
                        psalm.psalm_number,
                        _dt_to_str(datetime.now(UTC)),
                    ),
                )
            except sqlite3.Error:
                conn.rollback()
                raise
            conn.commit()
