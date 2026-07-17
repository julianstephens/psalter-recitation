from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from psalter.application.services.installation import InstallationReadinessService
from psalter.application.services.progress import ProgressService
from psalter.application.services.psalm_learning import PsalmLearningService
from psalter.application.services.review import ReviewService
from psalter.web.dependencies import (
    get_installation_readiness,
    get_progress_service,
    get_psalm_learning_service,
    get_review_service,
)
from psalter.web.schemas import serialize_progress, serialize_psalm_progress_item

router = APIRouter(prefix="/api/v1", tags=["progress"])


@router.get("/progress")
def get_progress(
    progress_service: Annotated[ProgressService, Depends(get_progress_service)],
    psalm_learning_service: Annotated[PsalmLearningService, Depends(get_psalm_learning_service)],
    review_service: Annotated[ReviewService, Depends(get_review_service)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    due_by_psalm: dict[str, int] = {}
    for item in review_service.get_due_psalm_reviews():
        due_by_psalm[item.psalm_id] = due_by_psalm.get(item.psalm_id, 0) + 1
    psalms = [
        serialize_psalm_progress_item(item, reviews_due=due_by_psalm.get(item.psalm_id, 0))
        for item in psalm_learning_service.list_progress()
    ]
    return serialize_progress(summary=asdict(progress_service.summary()), psalms=psalms)
