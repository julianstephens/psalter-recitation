from psalter.application.services.masking import mask_text


def test_masking_is_deterministic_and_progressively_harder() -> None:
    canonical = "The LORD is my shepherd\nI shall not want"
    first = mask_text(canonical, passage_id="p1", level=1)
    second = mask_text(canonical, passage_id="p1", level=1)
    harder = mask_text(canonical, passage_id="p1", level=3)
    assert first == second
    assert harder.count("_") >= first.count("_")


def test_masking_keeps_at_least_one_visible_word_per_nonblank_line_mid_levels() -> None:
    canonical = "The LORD is my shepherd\nHe restoreth my soul"
    masked = mask_text(canonical, passage_id="p2", level=2)
    for line in masked.splitlines():
        if line.strip():
            assert any(not token.startswith("_") for token in line.split())
