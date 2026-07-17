from psalter.application.services.normalization import normalize_text, normalize_tokens


def test_normalization_handles_case_and_punctuation() -> None:
    assert normalize_text("“The LORD is my shepherd.”") == "the lord is my shepherd"
    assert normalize_text("THE LORD IS MY SHEPHERD") == "the lord is my shepherd"


def test_normalization_ignores_standalone_verse_numbers_and_whitespace() -> None:
    assert normalize_tokens("1   The   LORD\n2 is my shepherd") == (
        "the",
        "lord",
        "is",
        "my",
        "shepherd",
    )


def test_normalization_does_not_stem_words() -> None:
    assert normalize_text("leadeth") != normalize_text("leads")
