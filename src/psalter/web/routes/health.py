from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from psalter.application.services.installation import PsalmCatalogInstaller
from psalter.bootstrap import Container
from psalter.web.dependencies import get_container, get_installer
from psalter.web.schemas import serialize_health, serialize_readiness

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return serialize_health()


@router.get("/readiness")
def readiness(
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    return serialize_readiness(
        settings=installer.get_settings(),
        installed_translations=installer.list_installed_translations(),
        config=container.config,
    )
