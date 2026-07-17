from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from psalter.application.errors import TranslationNotSupportedError
from psalter.application.services.installation import PsalmCatalogInstaller
from psalter.bootstrap import Container
from psalter.web.dependencies import get_container, get_installer
from psalter.web.schemas import serialize_installation, serialize_translation

router = APIRouter(prefix="/api/v1", tags=["installation"])


class InstallationRequest(BaseModel):
    translation_id: str = Field(min_length=1)
    set_as_default: bool = False


class ResumeRequest(BaseModel):
    translation_id: str | None = None
    set_as_default: bool = False


@router.get("/installation")
def get_installation(
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    return serialize_installation(
        settings=installer.get_settings(),
        installed_translations=installer.list_installed_translations(),
        config=container.config,
    )


@router.get("/translations")
def list_translations(
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
) -> dict[str, object]:
    return {"items": [serialize_translation(item) for item in installer.list_translations()]}


@router.post("/installation")
def initialize_installation(
    payload: InstallationRequest,
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    result = installer.initialize(
        payload.translation_id,
        set_as_default=payload.set_as_default,
    )
    return serialize_installation(
        settings=installer.get_settings(),
        installed_translations=installer.list_installed_translations(),
        config=container.config,
        result=result,
    )


@router.post("/installation/resume")
def resume_installation(
    payload: ResumeRequest,
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    translation_id = _resolve_translation_id(installer, payload.translation_id)
    result = installer.initialize(
        translation_id,
        resume=True,
        set_as_default=payload.set_as_default,
    )
    return serialize_installation(
        settings=installer.get_settings(),
        installed_translations=installer.list_installed_translations(),
        config=container.config,
        result=result,
    )


@router.post("/installation/repair")
def repair_installation(
    payload: ResumeRequest,
    installer: Annotated[PsalmCatalogInstaller, Depends(get_installer)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    translation_id = _resolve_translation_id(installer, payload.translation_id)
    result = installer.initialize(
        translation_id,
        repair=True,
        set_as_default=payload.set_as_default,
    )
    return serialize_installation(
        settings=installer.get_settings(),
        installed_translations=installer.list_installed_translations(),
        config=container.config,
        result=result,
    )


def _resolve_translation_id(installer: PsalmCatalogInstaller, explicit: str | None) -> str:
    if explicit is not None and explicit.strip():
        return explicit
    settings = installer.get_settings()
    if settings is None or settings.default_translation_id is None:
        raise TranslationNotSupportedError("A translation_id is required for this operation.")
    return settings.default_translation_id
