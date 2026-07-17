from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from psalter.application.errors import (
    ApplicationError,
    CatalogInstallationFailedError,
    CatalogRepairUnsafeError,
    CatalogValidationFailedError,
    InstallationAlreadyReadyError,
    InstallationIncompleteError,
    InstallationNotReadyError,
    PsalmDownloadFailedError,
    PsalmPayloadInvalidError,
    ScriptureProviderUnavailableError,
    TranslationCatalogUnavailableError,
    TranslationChangeBlockedError,
    TranslationNotSupportedError,
)
from psalter.application.services.psalm import build_complete_psalm_bundle
from psalter.application.services.segmentation import PsalmSegmentationPolicy
from psalter.domain.installation import CatalogStatus, InstallationSettings
from psalter.domain.passage import PassageKind
from psalter.ports.clock import Clock
from psalter.ports.installation_repository import (
    CatalogImportProgressRepository,
    InstallationSettingsRepository,
    PsalmCatalogCommitter,
)
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.psalm_repository import PsalmRepository
from psalter.ports.scripture_catalog_provider import (
    ScriptureCatalogProvider,
    TranslationInfo,
)

_DEFAULT_INSTALLATION_ID = 1
_DEFAULT_CATALOG_VERSION = "catalog-v1"


@dataclass(frozen=True, slots=True)
class CatalogInstallationResult:
    translation_id: str
    translation_name: str
    imported_psalm_count: int
    skipped_psalm_count: int


class InstallationReadinessService:
    def __init__(self, settings: InstallationSettingsRepository) -> None:
        self._settings = settings

    def require_ready(self) -> InstallationSettings:
        settings = self._settings.get_settings()
        if settings is None or settings.catalog_status is CatalogStatus.NOT_STARTED:
            raise InstallationNotReadyError(
                "Psalter is not fully initialized.\nRun `psalter init` to install a translation."
            )
        if settings.catalog_status is not CatalogStatus.READY:
            raise InstallationIncompleteError(
                "Psalter installation is incomplete.\nRun `psalter init --resume`."
            )
        return settings


class PsalmCatalogInstaller:
    def __init__(
        self,
        *,
        provider_name: str,
        provider: ScriptureCatalogProvider,
        settings: InstallationSettingsRepository,
        progress: CatalogImportProgressRepository,
        committer: PsalmCatalogCommitter,
        psalms: PsalmRepository,
        passages: PassageRepository,
        segmentation_policy: PsalmSegmentationPolicy,
        clock: Clock,
        required_psalm_numbers: tuple[int, ...] = tuple(range(1, 151)),
    ) -> None:
        self._provider_name = provider_name
        self._provider = provider
        self._settings = settings
        self._progress = progress
        self._committer = committer
        self._psalms = psalms
        self._passages = passages
        self._segmentation_policy = segmentation_policy
        self._clock = clock
        self._required_psalm_numbers = required_psalm_numbers

    def list_translations(self) -> tuple[TranslationInfo, ...]:
        return tuple(item for item in self._provider.list_translations() if item.supports_psalms)

    def get_settings(self) -> InstallationSettings | None:
        return self._settings.get_settings()

    def initialize(
        self,
        translation_id: str,
        *,
        resume: bool = False,
        repair: bool = False,
    ) -> CatalogInstallationResult:
        now = self._clock.now()
        selected = self._resolve_selected_translation(translation_id)
        current = self._settings.get_settings()
        changing_translation = (
            current is not None
            and current.default_translation_id is not None
            and current.default_translation_id.casefold() != selected.id.casefold()
        )
        if (
            current is not None
            and current.catalog_status is CatalogStatus.READY
            and current.default_translation_id is not None
            and current.default_translation_id.casefold() == selected.id.casefold()
            and not resume
            and not repair
        ):
            raise InstallationAlreadyReadyError(
                f"Psalter is already initialized with {current.default_translation_id}."
            )
        if changing_translation and current is not None:
            if self._committer.has_any_learning_history():
                raise TranslationChangeBlockedError(
                    "Cannot replace the installed translation because learning history exists.\n"
                    "Translation migration and multi-translation support are not implemented."
                )
            if not repair:
                raise TranslationChangeBlockedError(
                    "Translation replacement requires explicit repair mode.\n"
                    f"Run `psalter init --translation {selected.id} --repair`."
                )
            if current.default_translation_id is not None:
                self._committer.clear_translation_catalog(current.default_translation_id)

        base = current or InstallationSettings(
            id=_DEFAULT_INSTALLATION_ID,
            scripture_provider=self._provider_name,
            default_translation_id=None,
            default_translation_name=None,
            catalog_status=CatalogStatus.NOT_STARTED,
            catalog_version=None,
            initialized_at=None,
            updated_at=now,
            last_error=None,
        )
        if base.catalog_status is CatalogStatus.READY and (repair or changing_translation):
            installing = base.restart_installation(
                scripture_provider=self._provider_name,
                translation_id=selected.id,
                translation_name=selected.name,
                when=now,
            )
        else:
            installing = base.begin_installation(
                scripture_provider=self._provider_name,
                translation_id=selected.id,
                translation_name=selected.name,
                when=now,
            )
        self._settings.upsert(installing)

        imported = 0
        skipped = 0
        imported_numbers = self._progress.list_imported_psalm_numbers(installing.id)
        for psalm_number in self._required_psalm_numbers:
            should_skip = (
                psalm_number in imported_numbers
                and self._is_psalm_bundle_valid(selected.id, psalm_number)
            )
            if should_skip:
                skipped += 1
                continue
            if self._is_psalm_bundle_valid(selected.id, psalm_number):
                self._progress.mark_imported(installing.id, psalm_number)
                imported_numbers.add(psalm_number)
                skipped += 1
                continue
            existing = self._psalms.get_by_translation_and_number(selected.id, psalm_number)
            if (
                repair
                and existing is not None
                and self._committer.has_psalm_learning_history(existing.id)
            ):
                reason = (
                    f"Repair refused for Psalm {psalm_number} ({selected.id}) because learning "
                    "history exists."
                )
                self._progress.mark_failed(installing.id, psalm_number, reason)
                failed = installing.mark_failed(reason=reason, when=self._clock.now())
                self._settings.upsert(failed)
                raise CatalogRepairUnsafeError(reason)
            self._progress.mark_pending(installing.id, psalm_number)
            try:
                imported_psalm = self._provider.fetch_psalm(selected.id, psalm_number)
                if imported_psalm.psalm_number != psalm_number:
                    raise PsalmPayloadInvalidError(
                        f"Failed to import Psalm {psalm_number} from {selected.id}: provider "
                        "response Psalm number did not match request."
                    )
                psalm, passages = build_complete_psalm_bundle(
                    translation_id=selected.id,
                    psalm_number=psalm_number,
                    verses=tuple(
                        (verse.verse_number, verse.canonical_text)
                        for verse in imported_psalm.verses
                    ),
                    segmentation_policy=self._segmentation_policy,
                )
                self._committer.replace_psalm_bundle(
                    installation_id=installing.id,
                    psalm=psalm,
                    passages=passages,
                )
                imported += 1
            except (ApplicationError, ValueError, TypeError, sqlite3.Error) as exc:
                reason = str(exc).strip() or "unknown installation failure"
                self._progress.mark_failed(installing.id, psalm_number, reason)
                failed = installing.mark_failed(reason=reason, when=self._clock.now())
                self._settings.upsert(failed)
                raise CatalogInstallationFailedError(reason) from exc

        if not self._validate_catalog(selected.id):
            reason = (
                f"Catalog validation failed for {selected.id}. "
                f"Run `psalter init --repair --translation {selected.id}`."
            )
            failed = installing.mark_failed(reason=reason, when=self._clock.now())
            self._settings.upsert(failed)
            raise CatalogValidationFailedError(reason)

        ready = installing.mark_ready(
            catalog_version=_DEFAULT_CATALOG_VERSION, when=self._clock.now()
        )
        self._settings.upsert(ready)
        return CatalogInstallationResult(
            translation_id=selected.id,
            translation_name=selected.name,
            imported_psalm_count=imported,
            skipped_psalm_count=skipped,
        )

    def _resolve_selected_translation(self, requested_translation_id: str) -> TranslationInfo:
        try:
            translations = self.list_translations()
            return _resolve_translation(translations, requested_translation_id)
        except (TranslationCatalogUnavailableError, ScriptureProviderUnavailableError):
            normalized = requested_translation_id.strip()
            if not normalized:
                raise
            try:
                probed = self._provider.fetch_psalm(normalized, 1)
            except (PsalmDownloadFailedError, PsalmPayloadInvalidError):
                raise
            canonical_id = probed.translation_id.strip() or normalized
            return TranslationInfo(
                id=canonical_id,
                name=canonical_id,
                language="unknown",
                supports_psalms=True,
            )

    def _is_psalm_bundle_valid(self, translation_id: str, psalm_number: int) -> bool:
        psalm = self._psalms.get_by_translation_and_number(translation_id, psalm_number)
        if psalm is None:
            return False
        sections = self._passages.list_by_psalm(psalm.id, kind=PassageKind.SECTION)
        consolidation = self._passages.get_consolidation_passage(psalm.id)
        if not sections or consolidation is None:
            return False
        if consolidation.start_verse != 1 or consolidation.end_verse != psalm.verse_count:
            return False
        expected_start = 1
        for section in sections:
            if section.start_verse != expected_start:
                return False
            if section.end_verse < section.start_verse:
                return False
            expected_start = section.end_verse + 1
            if section.segmentation_policy_version != self._segmentation_policy.version:
                return False
        if expected_start != psalm.verse_count + 1:
            return False
        return consolidation.segmentation_policy_version == self._segmentation_policy.version

    def _validate_catalog(self, translation_id: str) -> bool:
        psalm_numbers: set[int] = set()
        for psalm_number in self._required_psalm_numbers:
            if not self._is_psalm_bundle_valid(translation_id, psalm_number):
                return False
            psalm_numbers.add(psalm_number)
        return psalm_numbers == set(self._required_psalm_numbers)


def _resolve_translation(
    translations: tuple[TranslationInfo, ...],
    requested: str,
) -> TranslationInfo:
    normalized = requested.strip().casefold()
    if not normalized:
        raise TranslationNotSupportedError("Translation selection is required.")
    matches = [
        item
        for item in translations
        if item.id.casefold() == normalized or item.name.casefold() == normalized
    ]
    if not matches:
        raise TranslationNotSupportedError(f"Unsupported translation: {requested}")
    if len(matches) > 1:
        raise TranslationNotSupportedError(
            f"Translation selection is ambiguous: {requested}. Use a translation ID."
        )
    return matches[0]


def default_installation_settings(now: datetime | None = None) -> InstallationSettings:
    instant = now or datetime.now(UTC)
    return InstallationSettings(
        id=_DEFAULT_INSTALLATION_ID,
        scripture_provider="helloao",
        default_translation_id=None,
        default_translation_name=None,
        catalog_status=CatalogStatus.NOT_STARTED,
        catalog_version=None,
        initialized_at=None,
        updated_at=instant,
        last_error=None,
    )
