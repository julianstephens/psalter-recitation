import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from psalter.cli.app import app


def _env() -> dict[str, str]:
    return {"PSALTER_SCRIPTURE_PROVIDER": "mock"}


def _init_catalog(runner: CliRunner, data_dir: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "--translation", "BSB", "--data-dir", str(data_dir)],
        env=_env(),
    )
    assert result.exit_code == 0
    assert "Psalter is ready." in result.output


def test_psalter_init_installs_catalog(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--translation", "BSB", "--data-dir", str(tmp_path)],
        env=_env(),
    )
    assert result.exit_code == 0
    assert "Imported 150 Psalms." in result.output
    assert "Default translation: BSB." in result.output


def test_psalter_progress_requires_ready(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["progress", "--data-dir", str(tmp_path)], env=_env())
    assert result.exit_code == 1
    assert "Psalter is not fully initialized." in result.output


def test_psalter_progress_works_after_init(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)

    result = runner.invoke(app, ["progress", "--data-dir", str(tmp_path)], env=_env())
    assert result.exit_code == 0
    assert "Total passages:" in result.output
    assert "Reviews due: 0" in result.output


def test_psalm_show_uses_default_translation_after_init(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)

    result = runner.invoke(app, ["psalm", "show", "90", "--data-dir", str(tmp_path)], env=_env())
    assert result.exit_code == 0
    assert "Psalm 90" in result.output
    assert "Translation: BSB" in result.output
    assert "BSB Psalm 90:1" in result.output


def test_reinit_reports_existing_ready_installation(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)

    result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)], env=_env())
    assert result.exit_code == 0
    assert "already initialized with BSB" in result.output


def test_translation_change_requires_explicit_replacement_mode(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)

    result = runner.invoke(
        app,
        ["init", "--translation", "KJV", "--data-dir", str(tmp_path)],
        env=_env(),
    )
    assert result.exit_code == 1
    assert "Translation replacement requires explicit repair mode." in result.output


def test_translation_change_with_repair_updates_default_when_no_history(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)

    result = runner.invoke(
        app,
        ["init", "--translation", "KJV", "--repair", "--data-dir", str(tmp_path)],
        env=_env(),
    )
    assert result.exit_code == 0
    settings = runner.invoke(app, ["settings", "--data-dir", str(tmp_path)], env=_env())
    assert settings.exit_code == 0
    assert "Default translation: KJV" in settings.output


def test_translation_change_repair_is_blocked_when_learning_history_exists(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)
    _seed_learning_history(tmp_path)

    result = runner.invoke(
        app,
        ["init", "--translation", "KJV", "--repair", "--data-dir", str(tmp_path)],
        env=_env(),
    )
    assert result.exit_code == 1
    assert "learning history exists" in result.output


def test_repair_refuses_invalid_psalm_replacement_when_history_exists(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_catalog(runner, tmp_path)
    _seed_learning_history(tmp_path)

    db_path = tmp_path / "psalter.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE passages
            SET segmentation_policy_version = 'broken-v1'
            WHERE psalm_id = 'bsb-psalm-1' AND kind = 'section'
            """
        )
        before_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE passage_id = ?",
                ("bsb-psalm-1-1-3",),
            ).fetchone()[0]
        )
    assert before_count == 1

    result = runner.invoke(
        app,
        ["init", "--translation", "BSB", "--repair", "--data-dir", str(tmp_path)],
        env=_env(),
    )
    assert result.exit_code == 1
    assert "Repair refused for Psalm 1 (BSB) because learning history exists." in result.output

    with sqlite3.connect(db_path) as conn:
        after_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE passage_id = ?",
                ("bsb-psalm-1-1-3",),
            ).fetchone()[0]
        )
    assert after_count == 1


def _seed_learning_history(data_dir: Path) -> None:
    db_path = data_dir / "psalter.db"
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            INSERT INTO learning_sessions(
                id, passage_id, phase, practice_level, successful_blank_recitations,
                started_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "seed-history-session",
                "bsb-psalm-1-1-3",
                "ready_for_recitation",
                4,
                0,
                now,
                now,
                None,
            ),
        )
