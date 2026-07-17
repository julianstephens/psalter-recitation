from __future__ import annotations

from dataclasses import dataclass

from psalter.domain.errors import InvariantViolationError


@dataclass(frozen=True, slots=True)
class Passage:
    id: str
    translation_id: str
    psalm_number: int
    start_verse: int
    end_verse: int
    canonical_text: str

    def __post_init__(self) -> None:
        if self.psalm_number <= 0:
            raise InvariantViolationError("Psalm number must be positive")
        if self.start_verse <= 0 or self.end_verse <= 0:
            raise InvariantViolationError("Verse numbers must be positive")
        if self.end_verse < self.start_verse:
            raise InvariantViolationError("End verse must not precede start verse")
        if not self.canonical_text.strip():
            raise InvariantViolationError("Canonical text must not be blank")

    @property
    def reference(self) -> str:
        return f"Psalm {self.psalm_number}:{self.start_verse}-{self.end_verse}"
