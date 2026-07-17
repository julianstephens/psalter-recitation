from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from psalter.application.dto import (
    PsalmDetailDTO,
    PsalmLearningScreenDTO,
    PsalmProgressDTO,
    PsalmReviewItemDTO,
)
from psalter.application.services.installation import CatalogInstallationResult
from psalter.config import AppConfig
from psalter.domain.installation import InstallationSettings
from psalter.ports.installation_repository import InstalledTranslation
from psalter.ports.scripture_catalog_provider import TranslationInfo


def serialize_health() -> dict[str, str]:
    return {"status": "ok"}


def serialize_readiness(
    *,
    settings: InstallationSettings | None,
    installed_translations: tuple[InstalledTranslation, ...],
    config: AppConfig,
) -> dict[str, object]:
    return {
        "status": "ok",
        "storage_ready": True,
        "installation": serialize_installation(
            settings=settings,
            installed_translations=installed_translations,
            config=config,
        ),
    }


def serialize_installation(
    *,
    settings: InstallationSettings | None,
    installed_translations: tuple[InstalledTranslation, ...],
    config: AppConfig,
    result: CatalogInstallationResult | None = None,
) -> dict[str, object]:
    default_translation_id = (
        settings.default_translation_id if settings is not None else config.default_translation_id
    )
    items = [
        {
            "translation_id": item.translation_id,
            "psalm_count": item.psalm_count,
            "is_default": item.translation_id == default_translation_id,
        }
        for item in installed_translations
    ]
    payload: dict[str, object] = {
        "catalog_status": settings.catalog_status.value if settings is not None else "not_started",
        "scripture_provider": (
            settings.scripture_provider if settings is not None else config.scripture_provider
        ),
        "default_translation_id": default_translation_id,
        "default_translation_name": settings.default_translation_name
        if settings is not None
        else None,
        "catalog_version": settings.catalog_version if settings is not None else None,
        "initialized_at": _serialize_datetime(settings.initialized_at if settings else None),
        "updated_at": _serialize_datetime(settings.updated_at if settings else None),
        "last_error": settings.last_error if settings is not None else None,
        "installed_translations": items,
        "is_ready": settings is not None and settings.catalog_status.value == "ready",
    }
    if result is not None:
        payload["result"] = {
            "installed_translation_id": result.installed_translation_id,
            "installed_translation_name": result.installed_translation_name,
            "default_translation_id": result.default_translation_id,
            "default_translation_name": result.default_translation_name,
            "imported_psalm_count": result.imported_psalm_count,
            "skipped_psalm_count": result.skipped_psalm_count,
            "default_changed": result.default_changed,
        }
    return payload


def serialize_translation(item: TranslationInfo) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "language": item.language,
        "supports_psalms": item.supports_psalms,
    }


def serialize_psalm_progress_item(
    item: PsalmProgressDTO,
    *,
    reviews_due: int | None = None,
) -> dict[str, object]:
    return {
        "psalm_id": item.psalm_id,
        "translation_id": item.translation_id,
        "psalm_number": item.psalm_number,
        "status": item.status.value,
        "section_count": item.section_count,
        "sections_learned": item.sections_learned,
        "current_section_label": item.current_section_label,
        "reviews_due": item.reviews_due if reviews_due is None else reviews_due,
        "consolidation_available": item.consolidation_available,
    }


def serialize_psalm_detail(
    detail: PsalmDetailDTO,
    *,
    progress: PsalmProgressDTO,
    reviews_due: int,
) -> dict[str, object]:
    return {
        "id": detail.id,
        "translation_id": detail.translation_id,
        "psalm_number": detail.psalm_number,
        "canonical_text": detail.canonical_text,
        "verse_count": detail.verse_count,
        "completeness": detail.completeness.value,
        "verses": [
            {"verse_number": verse.verse_number, "canonical_text": verse.canonical_text}
            for verse in detail.verses
        ],
        "learning": serialize_psalm_progress_item(progress, reviews_due=reviews_due),
    }


def serialize_review_item(item: PsalmReviewItemDTO) -> dict[str, object]:
    return {
        "psalm_id": item.psalm_id,
        "translation_id": item.translation_id,
        "psalm_number": item.psalm_number,
        "reason": item.reason,
        "due_label": item.due_label,
        "next_review_at": _serialize_datetime(item.next_review_at),
        "passage_id": item.passage_id,
    }


def serialize_progress(
    *,
    summary: Mapping[str, Any],
    psalms: list[dict[str, object]],
) -> dict[str, object]:
    return {"summary": dict(summary), "psalms": psalms}


def serialize_settings(
    *,
    settings: InstallationSettings | None,
    installed_translations: tuple[InstalledTranslation, ...],
    config: AppConfig,
) -> dict[str, object]:
    installation = serialize_installation(
        settings=settings,
        installed_translations=installed_translations,
        config=config,
    )
    return {
        "catalog_status": installation["catalog_status"],
        "scripture_provider": installation["scripture_provider"],
        "default_translation_id": installation["default_translation_id"],
        "default_translation_name": installation["default_translation_name"],
        "initialized_at": installation["initialized_at"],
        "last_error": installation["last_error"],
        "installed_translations": installation["installed_translations"],
        "log_level": config.log_level,
    }


def serialize_learning_screen(screen: PsalmLearningScreenDTO) -> dict[str, object]:
    payload: dict[str, object] = {
        "screen": screen.screen.value,
        "psalm_number": screen.view.psalm.psalm_number,
        "translation_id": screen.view.psalm.translation_id,
        "status": screen.view.plan.status.value,
        "section_count": screen.view.section_count,
        "sections_learned": screen.view.sections_learned,
        "consolidation_available": screen.view.consolidation_available,
        "active_target": (
            {
                "token": screen.active_target.token,
                "label": screen.active_target.label,
                "kind": screen.active_target.kind.value,
            }
            if screen.active_target is not None
            else None
        ),
        "active_passage": (
            {
                "id": screen.view.active_passage.id,
                "start_verse": screen.view.active_passage.start_verse,
                "end_verse": screen.view.active_passage.end_verse,
                "canonical_text": screen.view.active_passage.canonical_text,
                "kind": screen.view.active_passage.kind.value,
            }
            if screen.view.active_passage is not None
            else None
        ),
        "practice": (
            {
                "masked_text": screen.practice.masked_text,
                "level": screen.practice.level,
                "max_level": screen.practice.max_level,
            }
            if screen.practice is not None
            else None
        ),
        "assessment": (
            {
                "result": screen.assessment.result.value,
                "weighted_accuracy": screen.assessment.weighted_accuracy,
                "omission_count": screen.assessment.omission_count,
                "substitution_count": screen.assessment.substitution_count,
                "insertion_count": screen.assessment.insertion_count,
                "longest_omitted_span": screen.assessment.longest_omitted_span,
                "remaining_successes_required": screen.assessment.remaining_successes_required,
            }
            if screen.assessment is not None
            else None
        ),
    }
    return payload


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
