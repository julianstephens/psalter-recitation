from pathlib import Path

from typer.testing import CliRunner

from psalter.cli.app import app


def _init_and_add_psalm(runner: CliRunner, data_dir: Path) -> None:
    init_result = runner.invoke(app, ["init", "--data-dir", str(data_dir)])
    assert init_result.exit_code == 0
    add_result = runner.invoke(
        app,
        [
            "psalm",
            "add",
            "23",
            "--data-dir",
            str(data_dir),
            "--translation-id",
            "esv",
            "--verse",
            "1:The LORD is my shepherd.",
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


def test_psalm_add_list_show_and_passage_inspection(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_psalm(runner, tmp_path)

    psalm_list = runner.invoke(app, ["psalm", "list", "--data-dir", str(tmp_path)])
    assert psalm_list.exit_code == 0
    assert "Psalm 23 (esv)" in psalm_list.output

    psalm_show = runner.invoke(app, ["psalm", "show", "23", "--data-dir", str(tmp_path)])
    assert psalm_show.exit_code == 0
    assert "The LORD is my shepherd." in psalm_show.output

    passage_list = runner.invoke(
        app,
        ["passage", "list", "--psalm", "23", "--data-dir", str(tmp_path)],
    )
    assert passage_list.exit_code == 0
    assert "esv-psalm-23-1-1" in passage_list.output
    assert "esv-psalm-23-consolidation" in passage_list.output

    passage_show = runner.invoke(
        app,
        ["passage", "show", "esv-psalm-23-1-1", "--data-dir", str(tmp_path)],
    )
    assert passage_show.exit_code == 0
    assert "The LORD is my shepherd." in passage_show.output


def test_typed_learn_flow_works_without_audio_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_psalm(runner, tmp_path)
    result = runner.invoke(
        app,
        ["learn", "23", "--data-dir", str(tmp_path)],
        input=(
            "\n\n\n\n\n\n\n"
            "the lord is my shepherd\n.done\n"
            "\n"
            "the lord is my shepherd\n.done\n"
            "\n\n"
            "the lord is my shepherd\n.done\n"
            "\n"
            "the lord is my shepherd\n.done\n"
        ),
    )
    assert result.exit_code == 0
    assert "All sections learned. Entering whole-Psalm consolidation." in result.output
    assert "Whole Psalm learned." in result.output


def test_spoken_learn_requires_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_psalm(runner, tmp_path)
    result = runner.invoke(
        app,
        ["learn", "23", "--data-dir", str(tmp_path)],
        input="\n\n\n\n\n\nspoken\n\n",
    )
    assert result.exit_code == 1
    assert "Spoken recitation is not configured" in result.output


def test_progress_and_review_are_psalm_labeled(tmp_path: Path) -> None:
    runner = CliRunner()
    _init_and_add_psalm(runner, tmp_path)

    progress_result = runner.invoke(app, ["progress", "--data-dir", str(tmp_path)])
    assert progress_result.exit_code == 0
    assert "Psalm 23 - esv" in progress_result.output
    assert "Sections learned: 0/1" in progress_result.output

    review_result = runner.invoke(app, ["review", "--data-dir", str(tmp_path)])
    assert review_result.exit_code == 0
    assert "No reviews due." in review_result.output


def test_passage_add_supports_multiple_partial_sections(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)])
    assert init_result.exit_code == 0

    first = runner.invoke(
        app,
        [
            "passage",
            "add",
            "--data-dir",
            str(tmp_path),
            "--translation-id",
            "esv",
            "--psalm",
            "90",
            "--start-verse",
            "1",
            "--end-verse",
            "4",
            "--text",
            "Lord, thou hast been our dwelling place.",
        ],
    )
    assert first.exit_code == 0

    second = runner.invoke(
        app,
        [
            "passage",
            "add",
            "--data-dir",
            str(tmp_path),
            "--translation-id",
            "esv",
            "--psalm",
            "90",
            "--start-verse",
            "5",
            "--end-verse",
            "8",
            "--text",
            "Thou carriest them away as with a flood.",
        ],
    )
    assert second.exit_code == 0

    listed = runner.invoke(
        app,
        ["passage", "list", "--psalm", "90", "--data-dir", str(tmp_path)],
    )
    assert listed.exit_code == 0
    assert "esv-psalm-90-1-4" in listed.output
    assert "esv-psalm-90-5-8" in listed.output
    assert listed.output.index("esv-psalm-90-1-4") < listed.output.index("esv-psalm-90-5-8")


def test_partial_passage_import_cannot_be_upgraded_with_psalm_add(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", "--data-dir", str(tmp_path)])
    assert init_result.exit_code == 0

    passage_result = runner.invoke(
        app,
        [
            "passage",
            "add",
            "--data-dir",
            str(tmp_path),
            "--translation-id",
            "esv",
            "--psalm",
            "90",
            "--start-verse",
            "1",
            "--end-verse",
            "4",
            "--text",
            "Lord, thou hast been our dwelling place.",
        ],
    )
    assert passage_result.exit_code == 0

    psalm_result = runner.invoke(
        app,
        [
            "psalm",
            "add",
            "90",
            "--data-dir",
            str(tmp_path),
            "--translation-id",
            "esv",
            "--verse",
            "1:Lord, thou hast been our dwelling place.",
            "--verse",
            "2:Before the mountains were brought forth.",
        ],
    )
    assert psalm_result.exit_code == 1
    assert "partial import" in psalm_result.output
