from __future__ import annotations

import re

from psalter.application.dto import PsalmDetailDTO, PsalmSummaryDTO, PsalmVerseDTO
from psalter.application.errors import InvalidPassageError, PsalmAlreadyExistsError
from psalter.application.services.segmentation import PsalmSegmentationPolicy
from psalter.domain.errors import InvariantViolationError
from psalter.domain.passage import Passage, PassageKind
from psalter.domain.psalm import Psalm, PsalmCompleteness, PsalmVerse
from psalter.ports.psalm_repository import PsalmRepository

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class PsalmService:
    def __init__(
        self,
        psalms: PsalmRepository,
        segmentation_policy: PsalmSegmentationPolicy,
    ) -> None:
        self._psalms = psalms
        self._segmentation_policy = segmentation_policy

    def add(
        self,
        *,
        translation_id: str,
        psalm_number: int,
        verses: tuple[tuple[int, str], ...],
    ) -> PsalmDetailDTO:
        psalm_id = build_psalm_id(translation_id=translation_id, psalm_number=psalm_number)
        existing = self._psalms.get_by_id(psalm_id)
        if existing is not None:
            if existing.completeness is PsalmCompleteness.PARTIAL:
                raise PsalmAlreadyExistsError(
                    f"Psalm {translation_id} {psalm_number} already exists as a partial import. "
                    "Upgrading a partial Psalm to a complete Psalm import is not supported yet."
                )
            raise PsalmAlreadyExistsError(
                f"Psalm already exists: {translation_id} Psalm {psalm_number}"
            )
        psalm, passages = build_complete_psalm_bundle(
            translation_id=translation_id,
            psalm_number=psalm_number,
            verses=verses,
            segmentation_policy=self._segmentation_policy,
        )
        self._psalms.add_psalm_bundle(psalm=psalm, passages=passages)
        return _to_detail_dto(psalm)

    def list_all(self) -> list[PsalmSummaryDTO]:
        return [_to_summary_dto(psalm) for psalm in self._psalms.list_all()]

    def get_by_translation_and_number(
        self,
        *,
        translation_id: str,
        psalm_number: int,
    ) -> PsalmDetailDTO | None:
        psalm = self._psalms.get_by_translation_and_number(translation_id, psalm_number)
        return _to_detail_dto(psalm) if psalm is not None else None


def build_psalm_id(*, translation_id: str, psalm_number: int) -> str:
    normalized_translation = _normalized_translation_id(translation_id)
    return f"{normalized_translation}-psalm-{psalm_number}"


def build_passage_id(
    *,
    translation_id: str,
    psalm_number: int,
    start_verse: int,
    end_verse: int,
) -> str:
    normalized_translation = _normalized_translation_id(translation_id)
    return f"{normalized_translation}-psalm-{psalm_number}-{start_verse}-{end_verse}"


def _normalized_translation_id(translation_id: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", translation_id.strip().casefold()).strip("-")
    if not normalized:
        raise InvalidPassageError("Translation ID must contain at least one letter or digit")
    return normalized


def build_complete_psalm_bundle(
    *,
    translation_id: str,
    psalm_number: int,
    verses: tuple[tuple[int, str], ...],
    segmentation_policy: PsalmSegmentationPolicy,
) -> tuple[Psalm, tuple[Passage, ...]]:
    psalm_id = build_psalm_id(translation_id=translation_id, psalm_number=psalm_number)
    try:
        psalm_verses = tuple(
            PsalmVerse(verse_number=verse_number, canonical_text=text)
            for verse_number, text in verses
        )
        canonical_text = "\n".join(verse.canonical_text for verse in psalm_verses).strip()
        psalm = Psalm(
            id=psalm_id,
            translation_id=translation_id.strip(),
            psalm_number=psalm_number,
            canonical_text=canonical_text,
            verse_count=len(psalm_verses),
            completeness=PsalmCompleteness.COMPLETE,
            verses=psalm_verses,
        )
    except InvariantViolationError as exc:
        raise InvalidPassageError(str(exc)) from exc

    sections = segmentation_policy.segment(psalm_verses)
    passages = tuple(
        Passage(
            id=build_passage_id(
                translation_id=translation_id,
                psalm_number=psalm_number,
                start_verse=definition.start_verse,
                end_verse=definition.end_verse,
            ),
            psalm_id=psalm.id,
            translation_id=psalm.translation_id,
            psalm_number=psalm.psalm_number,
            start_verse=definition.start_verse,
            end_verse=definition.end_verse,
            canonical_text=definition.canonical_text,
            sequence_number=definition.sequence_number,
            kind=PassageKind.SECTION,
            segmentation_policy_version=segmentation_policy.version,
        )
        for definition in sections
    ) + (
        Passage(
            id=f"{psalm.id}-consolidation",
            psalm_id=psalm.id,
            translation_id=psalm.translation_id,
            psalm_number=psalm.psalm_number,
            start_verse=1,
            end_verse=psalm.verse_count,
            canonical_text=psalm.canonical_text,
            sequence_number=len(sections) + 1,
            kind=PassageKind.CONSOLIDATION,
            segmentation_policy_version=segmentation_policy.version,
        ),
    )
    return psalm, passages


def _to_summary_dto(psalm: Psalm) -> PsalmSummaryDTO:
    return PsalmSummaryDTO(
        id=psalm.id,
        translation_id=psalm.translation_id,
        psalm_number=psalm.psalm_number,
        verse_count=psalm.verse_count,
        completeness=psalm.completeness,
    )


def _to_detail_dto(psalm: Psalm) -> PsalmDetailDTO:
    return PsalmDetailDTO(
        id=psalm.id,
        translation_id=psalm.translation_id,
        psalm_number=psalm.psalm_number,
        canonical_text=psalm.canonical_text,
        verse_count=psalm.verse_count,
        completeness=psalm.completeness,
        verses=tuple(
            PsalmVerseDTO(verse_number=verse.verse_number, canonical_text=verse.canonical_text)
            for verse in psalm.verses
        ),
    )
