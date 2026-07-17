from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from psalter.application.errors import (
    ApplicationError,
    InstallationAlreadyReadyError,
    InstallationIncompleteError,
    InstallationNotReadyError,
    InvalidLearningTransitionError,
    InvalidPassageError,
    LearningSessionNotFoundError,
    NoActivePassageError,
    PassageNotFoundError,
    PersistenceConflictError,
    PsalmLearningPlanConflictError,
    PsalmNotFoundError,
    PsalmTranslationAmbiguousError,
    StaleLearningTargetError,
    TranslationChangeBlockedError,
    TranslationNotSupportedError,
)

_ERROR_MAP: dict[type[ApplicationError], tuple[int, str]] = {
    PassageNotFoundError: (HTTPStatus.NOT_FOUND, "passage_not_found"),
    PsalmNotFoundError: (HTTPStatus.NOT_FOUND, "psalm_not_found"),
    LearningSessionNotFoundError: (HTTPStatus.NOT_FOUND, "learning_session_not_found"),
    NoActivePassageError: (HTTPStatus.CONFLICT, "no_active_passage"),
    PsalmTranslationAmbiguousError: (HTTPStatus.CONFLICT, "psalm_translation_ambiguous"),
    PsalmLearningPlanConflictError: (HTTPStatus.CONFLICT, "psalm_learning_plan_conflict"),
    PersistenceConflictError: (HTTPStatus.CONFLICT, "persistence_conflict"),
    StaleLearningTargetError: (HTTPStatus.CONFLICT, "stale_learning_target"),
    InvalidLearningTransitionError: (HTTPStatus.BAD_REQUEST, "invalid_learning_transition"),
    InvalidPassageError: (HTTPStatus.BAD_REQUEST, "invalid_passage"),
    TranslationNotSupportedError: (HTTPStatus.BAD_REQUEST, "translation_not_supported"),
    InstallationNotReadyError: (HTTPStatus.CONFLICT, "installation_not_ready"),
    InstallationIncompleteError: (HTTPStatus.CONFLICT, "installation_incomplete"),
    InstallationAlreadyReadyError: (HTTPStatus.CONFLICT, "installation_already_ready"),
    TranslationChangeBlockedError: (HTTPStatus.CONFLICT, "translation_change_blocked"),
}


def application_error_response(request: Request, exc: ApplicationError) -> JSONResponse:
    status_code, code = _resolve_error(exc)
    return build_error_response(
        request=request,
        status_code=status_code,
        code=code,
        message=str(exc),
        details={},
    )


def validation_error_response(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = {"issues": exc.errors()}
    return build_error_response(
        request=request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="invalid_request",
        message="Request validation failed.",
        details=details,
    )


def build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Mapping[str, Any],
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": dict(details),
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


def _resolve_error(exc: ApplicationError) -> tuple[int, str]:
    for error_type, resolved in _ERROR_MAP.items():
        if isinstance(exc, error_type):
            return resolved
    return (HTTPStatus.INTERNAL_SERVER_ERROR, "application_error")
