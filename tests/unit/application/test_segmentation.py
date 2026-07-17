from psalter.application.services.segmentation import WordCountSegmentationPolicy
from psalter.domain.psalm import PsalmVerse


def _verse(number: int, text: str) -> PsalmVerse:
    return PsalmVerse(verse_number=number, canonical_text=text)


def test_short_psalm_becomes_one_section() -> None:
    policy = WordCountSegmentationPolicy(
        target_words_per_passage=8,
        maximum_words_per_passage=12,
    )
    sections = policy.segment(
        (
            _verse(1, "Blessed is the man."),
            _verse(2, "His delight is in the law."),
        )
    )
    assert len(sections) == 1
    assert sections[0].start_verse == 1
    assert sections[0].end_verse == 2


def test_long_psalm_is_split_deterministically_without_overlap() -> None:
    policy = WordCountSegmentationPolicy(
        target_words_per_passage=6,
        maximum_words_per_passage=9,
        minimum_words_per_passage=3,
    )
    verses = (
        _verse(1, "One two three."),
        _verse(2, "Four five six."),
        _verse(3, "Seven eight nine."),
        _verse(4, "Ten eleven twelve."),
    )
    first = policy.segment(verses)
    second = policy.segment(verses)
    assert first == second
    assert [(item.start_verse, item.end_verse) for item in first] == [(1, 2), (3, 4)]


def test_short_trailing_section_is_merged_when_safe() -> None:
    policy = WordCountSegmentationPolicy(
        target_words_per_passage=5,
        maximum_words_per_passage=8,
        minimum_words_per_passage=3,
    )
    sections = policy.segment(
        (
            _verse(1, "One two three."),
            _verse(2, "Four five six."),
            _verse(3, "Seven."),
        )
    )
    assert len(sections) == 1
    assert sections[0].start_verse == 1
    assert sections[0].end_verse == 3
