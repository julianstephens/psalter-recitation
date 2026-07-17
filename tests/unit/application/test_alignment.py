from psalter.application.services.alignment import align_tokens
from psalter.domain.recitation import AlignmentKind


def test_alignment_exact_match() -> None:
    result = align_tokens(("a", "b"), ("a", "b"))
    assert [item.kind for item in result.operations] == [AlignmentKind.MATCH, AlignmentKind.MATCH]


def test_alignment_omission_and_insertion_and_substitution() -> None:
    omitted = align_tokens(("a", "b", "c"), ("a", "c"))
    assert omitted.omission_count == 1

    inserted = align_tokens(("a", "c"), ("a", "b", "c"))
    assert inserted.insertion_count == 1

    substituted = align_tokens(("leadeth",), ("leads",))
    assert substituted.substitution_count == 1


def test_alignment_deterministic_tie_breaking_prefers_substitution_over_omission_insertion() -> (
    None
):
    result = align_tokens(("a",), ("b",))
    assert result.operations[0].kind is AlignmentKind.SUBSTITUTION
