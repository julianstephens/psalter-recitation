from pathlib import Path

from psalter.adapters.persistence import SqliteDatabase, SqliteMigrator, migrations_dir


def test_sqlite_migrations_are_idempotent(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    migrator = SqliteMigrator(db, migrations_dir())

    first = migrator.apply_pending()
    second = migrator.apply_pending()

    assert first == ["001_initial.sql"]
    assert second == []


def test_sqlite_foreign_keys_enabled(tmp_path: Path) -> None:
    db = SqliteDatabase(path=tmp_path / "test.db")
    SqliteMigrator(db, migrations_dir()).apply_pending()

    with db.open_connection() as conn:
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()

    assert fk_status is not None
    assert int(fk_status[0]) == 1
