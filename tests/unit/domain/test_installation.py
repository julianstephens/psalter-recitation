from datetime import UTC, datetime

import pytest

from psalter.domain.errors import InvalidTransitionError, InvariantViolationError
from psalter.domain.installation import CatalogStatus, InstallationSettings


def _settings(status: CatalogStatus) -> InstallationSettings:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return InstallationSettings(
        id=1,
        scripture_provider="helloao",
        default_translation_id="BSB" if status is CatalogStatus.READY else None,
        default_translation_name="Berean Standard Bible" if status is CatalogStatus.READY else None,
        catalog_status=status,
        catalog_version="catalog-v1" if status is CatalogStatus.READY else None,
        initialized_at=now if status is CatalogStatus.READY else None,
        updated_at=now,
        last_error=None,
    )


def test_ready_installation_requires_default_translation() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvariantViolationError):
        InstallationSettings(
            id=1,
            scripture_provider="helloao",
            default_translation_id=None,
            default_translation_name=None,
            catalog_status=CatalogStatus.READY,
            catalog_version="catalog-v1",
            initialized_at=now,
            updated_at=now,
            last_error=None,
        )


def test_ready_installation_cannot_begin_without_explicit_replacement() -> None:
    ready = _settings(CatalogStatus.READY)
    with pytest.raises(InvalidTransitionError):
        ready.begin_installation(
            scripture_provider="helloao",
            translation_id="KJV",
            translation_name="King James Version",
            when=datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_failed_installation_transition_preserves_reason() -> None:
    not_started = _settings(CatalogStatus.NOT_STARTED)
    failed = not_started.mark_failed(
        reason="Failed to import Psalm 119 from BSB",
        when=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert failed.catalog_status is CatalogStatus.FAILED
    assert failed.last_error == "Failed to import Psalm 119 from BSB"


def test_ready_installation_can_change_default_translation() -> None:
    ready = _settings(CatalogStatus.READY)
    updated = ready.change_default_translation(
        translation_id="KJV",
        translation_name="King James Version",
        when=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert updated.default_translation_id == "KJV"
    assert updated.default_translation_name == "King James Version"
    assert updated.catalog_status is CatalogStatus.READY
