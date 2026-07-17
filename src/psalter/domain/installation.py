from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from psalter.domain.errors import InvalidTransitionError, InvariantViolationError


class CatalogStatus(StrEnum):
    NOT_STARTED = "not_started"
    INSTALLING = "installing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class InstallationSettings:
    id: int
    scripture_provider: str
    default_translation_id: str | None
    default_translation_name: str | None
    catalog_status: CatalogStatus
    catalog_version: str | None
    initialized_at: datetime | None
    updated_at: datetime
    last_error: str | None

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise InvariantViolationError("Installation settings id must be positive")
        if not self.scripture_provider.strip():
            raise InvariantViolationError("Scripture provider must not be blank")
        if self.catalog_status is CatalogStatus.READY:
            if not self.default_translation_id or not self.default_translation_name:
                raise InvariantViolationError("Ready installation requires a default translation")
            if self.initialized_at is None:
                raise InvariantViolationError("Ready installation requires initialized_at")

    def begin_installation(
        self,
        *,
        scripture_provider: str,
        translation_id: str,
        translation_name: str,
        when: datetime,
    ) -> InstallationSettings:
        if self.catalog_status is CatalogStatus.READY:
            raise InvalidTransitionError(
                "Ready installation cannot begin without explicit replacement"
            )
        return replace(
            self,
            scripture_provider=scripture_provider,
            default_translation_id=translation_id,
            default_translation_name=translation_name,
            catalog_status=CatalogStatus.INSTALLING,
            updated_at=when,
            last_error=None,
        )

    def restart_installation(
        self,
        *,
        scripture_provider: str,
        translation_id: str,
        translation_name: str,
        when: datetime,
    ) -> InstallationSettings:
        return replace(
            self,
            scripture_provider=scripture_provider,
            default_translation_id=translation_id,
            default_translation_name=translation_name,
            catalog_status=CatalogStatus.INSTALLING,
            updated_at=when,
            last_error=None,
        )

    def change_default_translation(
        self,
        *,
        translation_id: str,
        translation_name: str,
        when: datetime,
    ) -> InstallationSettings:
        if self.catalog_status is not CatalogStatus.READY:
            raise InvalidTransitionError(
                "Default translation can only change on a ready installation"
            )
        return replace(
            self,
            default_translation_id=translation_id,
            default_translation_name=translation_name,
            updated_at=when,
            last_error=None,
        )

    def mark_ready(
        self,
        *,
        catalog_version: str,
        when: datetime,
    ) -> InstallationSettings:
        return replace(
            self,
            catalog_status=CatalogStatus.READY,
            catalog_version=catalog_version,
            initialized_at=when,
            updated_at=when,
            last_error=None,
        )

    def clear_last_error(self, *, when: datetime) -> InstallationSettings:
        return replace(self, updated_at=when, last_error=None)

    def record_last_error(self, *, reason: str, when: datetime) -> InstallationSettings:
        message = reason.strip()
        if not message:
            raise InvariantViolationError("Failure reason must not be blank")
        return replace(self, updated_at=when, last_error=message)

    def mark_failed(self, *, reason: str, when: datetime) -> InstallationSettings:
        message = reason.strip()
        if not message:
            raise InvariantViolationError("Failure reason must not be blank")
        return replace(
            self,
            catalog_status=CatalogStatus.FAILED,
            updated_at=when,
            last_error=message,
        )
