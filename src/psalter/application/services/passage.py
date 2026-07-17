from __future__ import annotations

import re

from psalter.application.dto import PassageDetailDTO, PassageSummaryDTO
from psalter.application.errors import (
    InvalidPassageError,
    PassageAlreadyExistsError,
    PassageNotFoundError,
)
from psalter.domain.errors import InvariantViolationError
from psalter.domain.passage import Passage
from psalter.ports.passage_repository import PassageRepository

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class PassageService:
    def __init__(self, passages: PassageRepository) -> None:
        self._passages = passages

    def add(
        self,
        translation_id: str,
        psalm_number: int,
        start_verse: int,
        end_verse: int,
        canonical_text: str,
    ) -> PassageDetailDTO:
        passage_id = _build_passage_id(
            translation_id=translation_id,
            psalm_number=psalm_number,
            start_verse=start_verse,
            end_verse=end_verse,
        )
        if self._passages.get_by_id(passage_id) is not None:
            raise PassageAlreadyExistsError(f"Passage already exists: {passage_id}")
        try:
            passage = Passage(
                id=passage_id,
                translation_id=translation_id.strip(),
                psalm_number=psalm_number,
                start_verse=start_verse,
                end_verse=end_verse,
                canonical_text=canonical_text,
            )
        except InvariantViolationError as exc:
            raise InvalidPassageError(str(exc)) from exc
        self._passages.add(passage)
        return _to_detail_dto(passage)

    def list_all(self) -> list[PassageSummaryDTO]:
        return [_to_summary_dto(item) for item in self._passages.list_all()]

    def get_by_id(self, passage_id: str) -> PassageDetailDTO:
        passage = self._passages.get_by_id(passage_id)
        if passage is None:
            raise PassageNotFoundError(f"Passage not found: {passage_id}")
        return _to_detail_dto(passage)


def _build_passage_id(
    translation_id: str,
    psalm_number: int,
    start_verse: int,
    end_verse: int,
) -> str:
    normalized_translation = _SLUG_PATTERN.sub("-", translation_id.strip().casefold()).strip("-")
    if not normalized_translation:
        raise InvalidPassageError("Translation ID must contain at least one letter or digit")
    return f"{normalized_translation}-psalm-{psalm_number}-{start_verse}-{end_verse}"


def _to_summary_dto(passage: Passage) -> PassageSummaryDTO:
    return PassageSummaryDTO(
        id=passage.id,
        translation_id=passage.translation_id,
        psalm_number=passage.psalm_number,
        start_verse=passage.start_verse,
        end_verse=passage.end_verse,
    )


def _to_detail_dto(passage: Passage) -> PassageDetailDTO:
    return PassageDetailDTO(
        id=passage.id,
        translation_id=passage.translation_id,
        psalm_number=passage.psalm_number,
        start_verse=passage.start_verse,
        end_verse=passage.end_verse,
        canonical_text=passage.canonical_text,
    )
