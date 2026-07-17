from pathlib import Path

from typer.testing import CliRunner

from psalter.cli.app import app


def test_psalter_init_succeeds(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Database ready at" in result.output


def test_psalter_progress_works_against_empty_database(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)])
    assert init_result.exit_code == 0

    progress_result = runner.invoke(app, ["progress", "--data-dir", str(tmp_path)])
    assert progress_result.exit_code == 0
    assert "Total passages: 0" in progress_result.output
    assert "Currently learning: 0" in progress_result.output
    assert "Learned: 0" in progress_result.output
    assert "Reviews due: 0" in progress_result.output
