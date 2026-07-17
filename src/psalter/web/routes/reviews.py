from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from psalter.application.services.installation import InstallationReadinessService
from psalter.application.services.review import ReviewService
from psalter.web.dependencies import get_installation_readiness, get_review_service
from psalter.web.schemas import serialize_review_item

router = APIRouter(prefix="/api/v1", tags=["reviews"])


@router.get("/reviews")
def list_reviews(
    review_service: Annotated[ReviewService, Depends(get_review_service)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
    status: Annotated[str, Query()] = "due",
) -> dict[str, object]:
    readiness.require_ready()
    items = review_service.get_due_psalm_reviews()
    if status != "due":
        items = []
    return {"items": [serialize_review_item(item) for item in items]}
