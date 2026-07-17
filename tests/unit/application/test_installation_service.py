from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from psalter.application.errors import PsalmDownloadFailedError, TranslationCatalogUnavailableError
from psalter.application.services.installation import PsalmCatalogInstaller
from psalter.application.services.segmentation import WordCountSegmentationPolicy
from psalter.domain.installation import InstallationSettings
from psalter.ports.scripture_catalog_provider import ImportedPsalm, ImportedPsalmVerse


@dataclass
class _FakeClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


class _FakeSettingsRepo:
    def __init__(self) -> None:
        self._settings: InstallationSettings | None = None

    def get_settings(self) -> InstallationSettings | None:
        return self._settings

    def upsert(self, settings: InstallationSettings) -> None:
        self._settings = settings


class _FakeProgressRepo:
    def mark_imported(self, installation_id: int, psalm_number: int) -> None:
        return None

    def mark_failed(self, installation_id: int, psalm_number: int, error: str) -> None:
        return None

    def mark_pending(self, installation_id: int, psalm_number: int) -> None:
        return None

    def list_imported_psalm_numbers(self, installation_id: int) -> set[int]:
        return set()


class _FakeCommitter:
    def replace_psalm_bundle(
        self,
        *,
        installation_id: int,
        psalm: object,
        passages: tuple[object, ...],
    ) -> None:
        return None

    def has_psalm_learning_history(self, psalm_id: str) -> bool:
        return False

    def has_any_learning_history(self) -> bool:
        return False

    def clear_translation_catalog(self, translation_id: str) -> None:
        return None


class _UnusedPsalmRepo:
    def get_by_translation_and_number(self, translation_id: str, psalm_number: int) -> None:
        return None


class _UnusedPassageRepo:
    def list_by_psalm(self, psalm_id: str, kind: object | None = None) -> list[object]:
        return []

    def get_consolidation_passage(self, psalm_id: str) -> None:
        return None


class _ListFailsProvider:
    def list_translations(self) -> tuple[object, ...]:
        raise TranslationCatalogUnavailableError("Scripture provider returned invalid JSON.")

    def fetch_psalm(self, translation_id: str, psalm_number: int) -> ImportedPsalm:
        return ImportedPsalm(
            translation_id=translation_id.upper(),
            psalm_number=psalm_number,
            verses=(ImportedPsalmVerse(verse_number=1, canonical_text="KJV Psalm 1:1"),),
        )


class _ListAndFetchFailProvider:
    def list_translations(self) -> tuple[object, ...]:
        raise TranslationCatalogUnavailableError("Scripture provider returned invalid JSON.")

    def fetch_psalm(self, translation_id: str, psalm_number: int) -> ImportedPsalm:
        raise PsalmDownloadFailedError("Failed to import Psalm 1 from KJV: HTTP 404")


def test_noninteractive_init_falls_back_to_probe_when_catalog_list_fails() -> None:
    installer = PsalmCatalogInstaller(
        provider_name="helloao",
        provider=_ListFailsProvider(),
        settings=_FakeSettingsRepo(),
        progress=_FakeProgressRepo(),
        committer=_FakeCommitter(),
        psalms=_UnusedPsalmRepo(),
        passages=_UnusedPassageRepo(),
        segmentation_policy=WordCountSegmentationPolicy(),
        clock=_FakeClock(datetime(2026, 1, 1, tzinfo=UTC)),
        required_psalm_numbers=(),
    )

    result = installer.initialize("kjv")

    assert result.translation_id == "KJV"
    assert result.imported_psalm_count == 0


def test_noninteractive_init_still_fails_when_probe_fails() -> None:
    installer = PsalmCatalogInstaller(
        provider_name="helloao",
        provider=_ListAndFetchFailProvider(),
        settings=_FakeSettingsRepo(),
        progress=_FakeProgressRepo(),
        committer=_FakeCommitter(),
        psalms=_UnusedPsalmRepo(),
        passages=_UnusedPassageRepo(),
        segmentation_policy=WordCountSegmentationPolicy(),
        clock=_FakeClock(datetime(2026, 1, 1, tzinfo=UTC)),
        required_psalm_numbers=(),
    )

    with pytest.raises(PsalmDownloadFailedError):
        installer.initialize("kjv")
