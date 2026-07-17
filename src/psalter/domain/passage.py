from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from psalter.domain.errors import InvariantViolationError


class PassageKind(StrEnum):
    SECTION = "section"
    CONSOLIDATION = "consolidation"


@dataclass(frozen=True, slots=True)
class Passage:
    id: str
    psalm_id: str
    translation_id: str
    psalm_number: int
    start_verse: int
    end_verse: int
    canonical_text: str
    sequence_number: int
    kind: PassageKind = PassageKind.SECTION
    segmentation_policy_version: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvariantViolationError("Passage ID must not be blank")
        if not self.psalm_id.strip():
            raise InvariantViolationError("Passage Psalm ID must not be blank")
        if not self.translation_id.strip():
            raise InvariantViolationError("Translation ID must not be blank")
        if self.psalm_number <= 0:
            raise InvariantViolationError("Psalm number must be positive")
        if self.start_verse <= 0 or self.end_verse <= 0:
            raise InvariantViolationError("Verse numbers must be positive")
        if self.end_verse < self.start_verse:
            raise InvariantViolationError("End verse must not precede start verse")
        if not self.canonical_text.strip():
            raise InvariantViolationError("Canonical text must not be blank")
        if self.sequence_number <= 0:
            raise InvariantViolationError("Sequence number must be positive")

    @property
    def reference(self) -> str:
        if self.kind is PassageKind.CONSOLIDATION:
            return f"Psalm {self.psalm_number}"
        return f"Psalm {self.psalm_number}:{self.start_verse}-{self.end_verse}"
