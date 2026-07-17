from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from psalter.domain.installation import InstallationSettings
from psalter.domain.passage import Passage
from psalter.domain.psalm import Psalm


@dataclass(frozen=True, slots=True)
class InstalledTranslation:
    translation_id: str
    psalm_count: int


class InstallationSettingsRepository(Protocol):
    def get_settings(self) -> InstallationSettings | None: ...

    def upsert(self, settings: InstallationSettings) -> None: ...


class CatalogImportProgressRepository(Protocol):
    def mark_imported(
        self,
        installation_id: int,
        translation_id: str,
        psalm_number: int,
    ) -> None: ...

    def mark_failed(
        self,
        installation_id: int,
        translation_id: str,
        psalm_number: int,
        error: str,
    ) -> None: ...

    def mark_pending(
        self,
        installation_id: int,
        translation_id: str,
        psalm_number: int,
    ) -> None: ...

    def list_imported_psalm_numbers(
        self,
        installation_id: int,
        translation_id: str,
    ) -> set[int]: ...


class PsalmCatalogCommitter(Protocol):
    def replace_psalm_bundle(
        self,
        *,
        installation_id: int,
        psalm: Psalm,
        passages: tuple[Passage, ...],
    ) -> None: ...

    def has_psalm_learning_history(self, psalm_id: str) -> bool: ...

    def has_any_learning_history(self) -> bool: ...

    def clear_translation_catalog(self, translation_id: str) -> None: ...

    def list_installed_translations(self) -> tuple[InstalledTranslation, ...]: ...
