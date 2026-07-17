import pytest

from psalter.domain.errors import InvariantViolationError
from psalter.domain.passage import Passage


def test_passage_valid_invariants() -> None:
    passage = Passage(
        id="p1",
        translation_id="esv",
        psalm_number=1,
        start_verse=1,
        end_verse=2,
        canonical_text="Blessed is the man.",
    )
    assert passage.reference == "Psalm 1:1-2"


@pytest.mark.parametrize(
    ("psalm_number", "start_verse", "end_verse", "canonical_text"),
    [
        (0, 1, 1, "x"),
        (1, 0, 1, "x"),
        (1, 1, 0, "x"),
        (1, 2, 1, "x"),
        (1, 1, 1, "   "),
    ],
)
def test_passage_invariant_violations(
    psalm_number: int,
    start_verse: int,
    end_verse: int,
    canonical_text: str,
) -> None:
    with pytest.raises(InvariantViolationError):
        Passage(
            id="p1",
            translation_id="esv",
            psalm_number=psalm_number,
            start_verse=start_verse,
            end_verse=end_verse,
            canonical_text=canonical_text,
        )
