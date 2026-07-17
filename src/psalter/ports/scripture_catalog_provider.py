from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranslationInfo:
    id: str
    name: str
    language: str
    supports_psalms: bool


@dataclass(frozen=True, slots=True)
class ImportedPsalmVerse:
    verse_number: int
    canonical_text: str


@dataclass(frozen=True, slots=True)
class ImportedPsalm:
    translation_id: str
    psalm_number: int
    verses: tuple[ImportedPsalmVerse, ...]


class ScriptureCatalogProvider(Protocol):
    def list_translations(self) -> tuple[TranslationInfo, ...]: ...

    def fetch_psalm(self, translation_id: str, psalm_number: int) -> ImportedPsalm: ...
