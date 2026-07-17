from datetime import UTC, datetime

import pytest

from psalter.domain.errors import InvalidTransitionError, InvariantViolationError
from psalter.domain.psalm import (
    Psalm,
    PsalmCompleteness,
    PsalmLearningPlan,
    PsalmLearningStatus,
    PsalmVerse,
)


def test_psalm_requires_ordered_unique_verses() -> None:
    with pytest.raises(InvariantViolationError):
        Psalm(
            id="esv-psalm-1",
            translation_id="esv",
            psalm_number=1,
            canonical_text="Verse two\nVerse one",
            verse_count=2,
            completeness=PsalmCompleteness.COMPLETE,
            verses=(
                PsalmVerse(verse_number=2, canonical_text="Verse two"),
                PsalmVerse(verse_number=1, canonical_text="Verse one"),
            ),
        )


def test_complete_psalm_plan_transitions_do_not_imply_whole_psalm_learned() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    plan = PsalmLearningPlan(
        psalm_id="esv-psalm-90",
        status=PsalmLearningStatus.LEARNING_SECTIONS,
        active_passage_id="esv-psalm-90-1-4",
        started_at=now,
        updated_at=now,
        completed_at=None,
    )
    consolidating = plan.begin_consolidation("esv-psalm-90-consolidation", now)
    assert consolidating.status is PsalmLearningStatus.CONSOLIDATING
    assert consolidating.completed_at is None


def test_learned_plan_cannot_regress() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    learned = PsalmLearningPlan(
        psalm_id="esv-psalm-90",
        status=PsalmLearningStatus.LEARNED,
        active_passage_id=None,
        started_at=now,
        updated_at=now,
        completed_at=now,
    )
    with pytest.raises(InvalidTransitionError):
        learned.activate_passage("esv-psalm-90-1-4", now)
