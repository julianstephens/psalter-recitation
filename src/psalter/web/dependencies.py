from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from psalter.application.services.installation import (
    InstallationReadinessService,
    PsalmCatalogInstaller,
)
from psalter.application.services.progress import ProgressService
from psalter.application.services.psalm import PsalmService
from psalter.application.services.psalm_learning import PsalmLearningService
from psalter.application.services.review import ReviewService
from psalter.application.services.workflow import PsalmLearningWorkflow
from psalter.bootstrap import Container


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


def get_installer(
    container: Annotated[Container, Depends(get_container)],
) -> PsalmCatalogInstaller:
    return container.installer


def get_installation_readiness(
    container: Annotated[Container, Depends(get_container)],
) -> InstallationReadinessService:
    return container.installation_readiness


def get_psalm_service(
    container: Annotated[Container, Depends(get_container)],
) -> PsalmService:
    return container.psalm_service


def get_psalm_learning_service(
    container: Annotated[Container, Depends(get_container)],
) -> PsalmLearningService:
    return container.psalm_learning_service


def get_review_service(
    container: Annotated[Container, Depends(get_container)],
) -> ReviewService:
    return container.review_service


def get_progress_service(
    container: Annotated[Container, Depends(get_container)],
) -> ProgressService:
    return container.progress_service


def get_learning_workflow(
    container: Annotated[Container, Depends(get_container)],
) -> PsalmLearningWorkflow:
    return PsalmLearningWorkflow(
        psalm_learning_service=container.psalm_learning_service,
        learning_service=container.learning_service,
        recitation_service=container.recitation_service,
        spoken_recitation_service=container.spoken_recitation_service,
    )
