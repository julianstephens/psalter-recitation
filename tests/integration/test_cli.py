from pathlib import Path

from typer.testing import CliRunner

from psalter.cli.app import app


def _init_and_add_passage(runner: CliRunner, data_dir: Path) -> None:
    init_result = runner.invoke(app, ["init", "--data-dir", str(data_dir)])
    assert init_result.exit_code == 0
    add_result = runner.invoke(
        app,
        [
            "passage",
            "add",
            "--data-dir",
            str(data_dir),
            "--translation-id",
            "esv",
            "--psalm",
            "23",
            "--start-verse",
            "1",
            "--end-verse",
            "1",
            "--text",
            "The LORD is my shepherd",
        ],
    )
    assert add_result.exit_code == 0


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


def test_typed_learn_flow_works_without_audio_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_passage(runner, tmp_path)
    result = runner.invoke(
        app,
        ["learn", "esv-psalm-23-1-1", "--data-dir", str(tmp_path)],
        input="\n\n\n\n\n\n\nthe lord is my shepherd\n.done\n\nthe lord is my shepherd\n.done\n",
    )
    assert result.exit_code == 0
    assert "Passage learned. Initial review scheduled for one day from now." in result.output


def test_spoken_learn_requires_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_passage(runner, tmp_path)
    result = runner.invoke(
        app,
        ["learn", "esv-psalm-23-1-1", "--data-dir", str(tmp_path)],
        input="\n\n\n\n\n\nspoken\n\n",
    )
    assert result.exit_code == 1
    assert "Spoken recitation is not configured" in result.output
