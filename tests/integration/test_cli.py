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
