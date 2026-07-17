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
    assert "Unseen passages: 0" in progress_result.output
    assert "Learned passages: 0" in progress_result.output
    assert "Reviews due: 0" in progress_result.output


def test_passage_add_list_show(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)])
    assert init_result.exit_code == 0

    add_result = runner.invoke(
        app,
        [
            "passage",
            "add",
            "--data-dir",
            str(tmp_path),
            "--translation-id",
            "esv",
            "--psalm",
            "23",
            "--start-verse",
            "1",
            "--end-verse",
            "1",
            "--text",
            "The LORD is my shepherd.",
        ],
    )
    assert add_result.exit_code == 0
    assert "Added passage esv-psalm-23-1-1" in add_result.output

    list_result = runner.invoke(app, ["passage", "list", "--data-dir", str(tmp_path)])
    assert list_result.exit_code == 0
    assert "esv-psalm-23-1-1" in list_result.output

    show_result = runner.invoke(
        app, ["passage", "show", "esv-psalm-23-1-1", "--data-dir", str(tmp_path)]
    )
    assert show_result.exit_code == 0
    assert "The LORD is my shepherd." in show_result.output
