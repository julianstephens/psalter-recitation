from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from psalter.application.errors import PsalmNotFoundError
from psalter.application.services.installation import InstallationReadinessService
from psalter.application.services.psalm import PsalmService
from psalter.application.services.psalm_learning import PsalmLearningService
from psalter.application.services.review import ReviewService
from psalter.web.dependencies import (
    get_installation_readiness,
    get_psalm_learning_service,
    get_psalm_service,
    get_review_service,
)
from psalter.web.schemas import serialize_psalm_detail, serialize_psalm_progress_item

router = APIRouter(prefix="/api/v1", tags=["psalms"])


@router.get("/psalms")
def list_psalms(
    psalm_service: Annotated[PsalmService, Depends(get_psalm_service)],
    psalm_learning_service: Annotated[PsalmLearningService, Depends(get_psalm_learning_service)],
    review_service: Annotated[ReviewService, Depends(get_review_service)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    due_by_psalm = _due_review_counts(review_service)
    progress_items = {
        (item.translation_id, item.psalm_number): item
        for item in psalm_learning_service.list_progress()
    }
    items = []
    for summary in psalm_service.list_all():
        progress = progress_items[(summary.translation_id, summary.psalm_number)]
        items.append(
            {
                "id": summary.id,
                "translation_id": summary.translation_id,
                "psalm_number": summary.psalm_number,
                "verse_count": summary.verse_count,
                "completeness": summary.completeness.value,
                "learning": serialize_psalm_progress_item(
                    progress,
                    reviews_due=due_by_psalm.get(progress.psalm_id, 0),
                ),
            }
        )
    return {"items": items}


@router.get("/psalms/{psalm_number}")
def get_psalm(
    psalm_number: int,
    psalm_service: Annotated[PsalmService, Depends(get_psalm_service)],
    psalm_learning_service: Annotated[PsalmLearningService, Depends(get_psalm_learning_service)],
    review_service: Annotated[ReviewService, Depends(get_review_service)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
    translation_id: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    readiness.require_ready()
    progress = psalm_learning_service.get_progress(
        psalm_number=psalm_number,
        translation_id=translation_id,
    )
    detail = psalm_service.get_by_translation_and_number(
        translation_id=progress.translation_id,
        psalm_number=psalm_number,
    )
    if detail is None:
        raise PsalmNotFoundError(
            f"Psalm {psalm_number} was not found for translation {progress.translation_id}."
        )
    due_by_psalm = _due_review_counts(review_service)
    return serialize_psalm_detail(
        detail,
        progress=progress,
        reviews_due=due_by_psalm.get(progress.psalm_id, 0),
    )


def _due_review_counts(review_service: ReviewService) -> dict[str, int]:
    due_by_psalm: dict[str, int] = {}
    for item in review_service.get_due_psalm_reviews():
        due_by_psalm[item.psalm_id] = due_by_psalm.get(item.psalm_id, 0) + 1
    return due_by_psalm
