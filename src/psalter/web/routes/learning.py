from __future__ import annotations

from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from psalter.application.services.installation import InstallationReadinessService
from psalter.application.services.workflow import PsalmLearningWorkflow
from psalter.bootstrap import Container
from psalter.web.dependencies import (
    get_container,
    get_installation_readiness,
    get_learning_workflow,
)
from psalter.web.schemas import serialize_learning_screen

router = APIRouter(prefix="/api/v1", tags=["learning"])


class LearningTargetRequest(BaseModel):
    translation_id: str | None = None
    target_token: str | None = None


class TypedRecitationRequest(LearningTargetRequest):
    text: str


@router.get("/psalms/{psalm_number}/learning")
def get_learning_state(
    psalm_number: int,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(workflow.start_or_resume(psalm_number=psalm_number))


@router.post("/psalms/{psalm_number}/learning/start")
def start_learning(
    psalm_number: int,
    payload: LearningTargetRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(
        workflow.start_or_resume(psalm_number=psalm_number, translation_id=payload.translation_id)
    )


@router.post("/psalms/{psalm_number}/learning/exposure/complete")
def complete_exposure(
    psalm_number: int,
    payload: LearningTargetRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(
        workflow.complete_exposure(
            psalm_number=psalm_number,
            translation_id=payload.translation_id,
            target_token=payload.target_token,
        )
    )


@router.post("/psalms/{psalm_number}/learning/practice/complete")
def complete_practice(
    psalm_number: int,
    payload: LearningTargetRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(
        workflow.complete_practice(
            psalm_number=psalm_number,
            translation_id=payload.translation_id,
            target_token=payload.target_token,
        )
    )


@router.post("/psalms/{psalm_number}/learning/practice/shadow-typing")
def submit_shadow_typing(
    psalm_number: int,
    payload: TypedRecitationRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    container: Annotated[Container, Depends(get_container)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    screen = workflow.start_or_resume(
        psalm_number=psalm_number,
        translation_id=payload.translation_id,
    )
    active = screen.view.active_passage
    if active is None:
        return serialize_learning_screen(screen)
    result = container.learning_service.submit_shadow_typing(active.id, payload.text)
    if result.accepted:
        return serialize_learning_screen(
            workflow.start_or_resume(
                psalm_number=psalm_number,
                translation_id=payload.translation_id,
            )
        )
    practice = container.learning_service.get_practice_view(
        active.id,
        mismatch_excerpt=result.mismatch_excerpt,
    )
    return serialize_learning_screen(replace(screen, practice=practice))


@router.post("/psalms/{psalm_number}/learning/reinforcement/resume")
def resume_reinforcement(
    psalm_number: int,
    payload: LearningTargetRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(
        workflow.resume_reinforcement(
            psalm_number=psalm_number,
            translation_id=payload.translation_id,
            target_token=payload.target_token,
        )
    )


@router.post("/psalms/{psalm_number}/learning/recitations/text")
def submit_typed_recitation(
    psalm_number: int,
    payload: TypedRecitationRequest,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
) -> dict[str, object]:
    readiness.require_ready()
    return serialize_learning_screen(
        workflow.submit_typed_recitation(
            psalm_number=psalm_number,
            translation_id=payload.translation_id,
            text=payload.text,
            target_token=payload.target_token,
        )
    )


@router.post("/psalms/{psalm_number}/learning/recitations/audio")
async def submit_audio_recitation(
    psalm_number: int,
    workflow: Annotated[PsalmLearningWorkflow, Depends(get_learning_workflow)],
    readiness: Annotated[InstallationReadinessService, Depends(get_installation_readiness)],
    audio: Annotated[UploadFile, File(...)],
    target_token: Annotated[str | None, Form()] = None,
    translation_id: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    readiness.require_ready()
    audio.file.seek(0)
    return serialize_learning_screen(
        workflow.submit_uploaded_audio(
            psalm_number=psalm_number,
            translation_id=translation_id,
            target_token=target_token,
            source=audio.file,
            content_type=audio.content_type or "application/octet-stream",
        )
    )
