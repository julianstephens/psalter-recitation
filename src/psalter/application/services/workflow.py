from __future__ import annotations

from collections.abc import Callable
from typing import BinaryIO

from psalter.application.dto import (
    LearningTargetDTO,
    PassageDetailDTO,
    PracticeViewDTO,
    PsalmLearningScreen,
    PsalmLearningScreenDTO,
    PsalmLearningViewDTO,
    RecitationAssessmentDTO,
    RecitationSubmission,
)
from psalter.application.errors import NoActivePassageError, StaleLearningTargetError
from psalter.application.services.learning import LearningService
from psalter.application.services.psalm_learning import PsalmLearningService
from psalter.application.services.recitation import RecitationService
from psalter.application.services.spoken_recitation import SpokenRecitationService
from psalter.domain.learning import LearningPhase
from psalter.domain.passage import PassageKind
from psalter.domain.psalm import PsalmLearningStatus
from psalter.domain.recitation import RecitationResult, RecitationSource


class PsalmLearningWorkflow:
    def __init__(
        self,
        *,
        psalm_learning_service: PsalmLearningService,
        learning_service: LearningService,
        recitation_service: RecitationService,
        spoken_recitation_service: SpokenRecitationService,
    ) -> None:
        self._psalm_learning_service = psalm_learning_service
        self._learning_service = learning_service
        self._recitation_service = recitation_service
        self._spoken_recitation_service = spoken_recitation_service

    def start_or_resume(
        self,
        *,
        psalm_number: int,
        translation_id: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.begin_or_resume(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        return self._to_actionable_screen(view)

    def complete_exposure(
        self,
        *,
        psalm_number: int,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        if active.kind is PassageKind.CONSOLIDATION:
            self._learning_service.complete_exposure_and_mark_ready(active.id)
        else:
            self._learning_service.complete_exposure(active.id)
        updated = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        return self._to_actionable_screen(updated)

    def complete_practice(
        self,
        *,
        psalm_number: int,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        self._learning_service.complete_practice_level(active.id)
        updated = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        return self._to_actionable_screen(updated)

    def submit_typed_recitation(
        self,
        *,
        psalm_number: int,
        text: str,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        assessment = self._recitation_service.submit_text(
            RecitationSubmission(
                passage_id=active.id,
                source=RecitationSource.TYPED,
                text=text,
            )
        )
        return self._screen_after_assessment(
            previous_view=view,
            previous_active=active,
            assessment=assessment,
        )

    def submit_spoken_transcript(
        self,
        *,
        psalm_number: int,
        transcript: str,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        assessment = self._recitation_service.submit_text(
            RecitationSubmission(
                passage_id=active.id,
                source=RecitationSource.SPEECH_TRANSCRIPT,
                text=transcript,
            )
        )
        return self._screen_after_assessment(
            previous_view=view,
            previous_active=active,
            assessment=assessment,
        )

    def submit_recorded_recitation(
        self,
        *,
        psalm_number: int,
        translation_id: str | None = None,
        target_token: str | None = None,
        wait_for_stop: Callable[[float | None], bool] | None = None,
        before_transcribe: Callable[[], None] | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        assessment = self._spoken_recitation_service.record_transcribe_and_submit(
            active.id,
            wait_for_stop=wait_for_stop,
            before_transcribe=before_transcribe,
        )
        return self._screen_after_assessment(
            previous_view=view,
            previous_active=active,
            assessment=assessment,
        )

    def submit_uploaded_audio(
        self,
        *,
        psalm_number: int,
        source: BinaryIO,
        content_type: str,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        assessment = self._spoken_recitation_service.prepare_transcribe_and_submit_uploaded(
            passage_id=active.id,
            source=source,
            content_type=content_type,
        )
        return self._screen_after_assessment(
            previous_view=view,
            previous_active=active,
            assessment=assessment,
        )

    def resume_reinforcement(
        self,
        *,
        psalm_number: int,
        translation_id: str | None = None,
        target_token: str | None = None,
    ) -> PsalmLearningScreenDTO:
        view = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        active = self._require_active_passage(view.active_passage)
        self._validate_target_token(view=view, target_token=target_token)
        self._learning_service.resume_reinforcement(active.id)
        updated = self._psalm_learning_service.get_learning_view(
            psalm_number=psalm_number,
            translation_id=translation_id,
        )
        return self._to_actionable_screen(updated)

    def _screen_after_assessment(
        self,
        *,
        previous_view: PsalmLearningViewDTO,
        previous_active: PassageDetailDTO,
        assessment: RecitationAssessmentDTO,
    ) -> PsalmLearningScreenDTO:
        if (
            assessment.result is RecitationResult.PASS
            and assessment.remaining_successes_required == 0
        ):
            updated = self._psalm_learning_service.advance_after_passage_learned(
                previous_view.psalm.id
            )
            return self._completion_screen(
                previous_active=previous_active,
                updated_view=updated,
                assessment=assessment,
            )
        updated = self._psalm_learning_service.get_learning_view(
            psalm_number=previous_view.psalm.psalm_number,
            translation_id=previous_view.psalm.translation_id,
        )
        if assessment.result is RecitationResult.MANUAL_REVIEW:
            return self._build_screen(
                screen=PsalmLearningScreen.MANUAL_REVIEW,
                view=updated,
                assessment=assessment,
            )
        return self._to_actionable_screen(updated, assessment=assessment)

    def _to_actionable_screen(
        self,
        view: PsalmLearningViewDTO,
        *,
        assessment: RecitationAssessmentDTO | None = None,
    ) -> PsalmLearningScreenDTO:
        if view.plan.status is PsalmLearningStatus.LEARNED:
            return self._build_screen(
                screen=PsalmLearningScreen.PSALM_COMPLETED,
                view=view,
                assessment=assessment,
            )
        if (
            view.plan.status is PsalmLearningStatus.CONSOLIDATING
            and not view.consolidation_available
        ):
            return self._build_screen(
                screen=PsalmLearningScreen.CONSOLIDATION_UNAVAILABLE,
                view=view,
                assessment=assessment,
            )
        active = self._require_active_passage(view.active_passage)
        session = self._learning_service.get_current_session(active.id)
        if session is None:
            raise NoActivePassageError(f"No learning session found for active passage {active.id}.")
        if session.phase is LearningPhase.LEARNED:
            updated = self._psalm_learning_service.advance_after_passage_learned(view.psalm.id)
            return self._to_actionable_screen(updated, assessment=assessment)
        if session.phase is LearningPhase.EXPOSURE:
            return self._build_screen(
                screen=PsalmLearningScreen.EXPOSURE,
                view=view,
                assessment=assessment,
            )
        if session.phase is LearningPhase.PRACTICE:
            return self._build_screen(
                screen=PsalmLearningScreen.PRACTICE,
                view=view,
                practice=self._learning_service.get_practice_view(active.id),
                assessment=assessment,
            )
        if session.phase is LearningPhase.READY_FOR_RECITATION:
            return self._build_screen(
                screen=PsalmLearningScreen.READY_FOR_RECITATION,
                view=view,
                assessment=assessment,
            )
        if session.phase is LearningPhase.NEEDS_REINFORCEMENT:
            return self._build_screen(
                screen=PsalmLearningScreen.REINFORCEMENT,
                view=view,
                assessment=assessment,
            )
        raise NoActivePassageError(f"Unsupported learning phase for active passage {active.id}.")

    def _completion_screen(
        self,
        *,
        previous_active: PassageDetailDTO,
        updated_view: PsalmLearningViewDTO,
        assessment: RecitationAssessmentDTO,
    ) -> PsalmLearningScreenDTO:
        if updated_view.plan.status is PsalmLearningStatus.LEARNED:
            return self._build_screen(
                screen=PsalmLearningScreen.PSALM_COMPLETED,
                view=updated_view,
                assessment=assessment,
            )
        if (
            updated_view.plan.status is PsalmLearningStatus.CONSOLIDATING
            and not updated_view.consolidation_available
        ):
            return self._build_screen(
                screen=PsalmLearningScreen.CONSOLIDATION_UNAVAILABLE,
                view=updated_view,
                assessment=assessment,
            )
        next_active = self._require_active_passage(updated_view.active_passage)
        if (
            previous_active.kind is PassageKind.SECTION
            and next_active.kind is PassageKind.CONSOLIDATION
        ):
            return self._build_screen(
                screen=PsalmLearningScreen.CONSOLIDATION_STARTED,
                view=updated_view,
                assessment=assessment,
            )
        if previous_active.kind is PassageKind.SECTION:
            return self._build_screen(
                screen=PsalmLearningScreen.SECTION_COMPLETED,
                view=updated_view,
                assessment=assessment,
            )
        return self._build_screen(
            screen=PsalmLearningScreen.PSALM_COMPLETED,
            view=updated_view,
            assessment=assessment,
        )

    def _build_screen(
        self,
        *,
        screen: PsalmLearningScreen,
        view: PsalmLearningViewDTO,
        practice: PracticeViewDTO | None = None,
        assessment: RecitationAssessmentDTO | None = None,
    ) -> PsalmLearningScreenDTO:
        active_target = (
            _build_target(view)
            if view.active_passage is not None and view.plan.active_passage_id
            else None
        )
        return PsalmLearningScreenDTO(
            screen=screen,
            view=view,
            active_target=active_target,
            practice=practice,
            assessment=assessment,
        )

    def _validate_target_token(
        self,
        *,
        view: PsalmLearningViewDTO,
        target_token: str | None,
    ) -> None:
        if target_token is None:
            return
        expected = _build_target(view)
        if target_token != expected.token:
            raise StaleLearningTargetError(
                "The active learning target has changed; refresh and retry."
            )

    def _require_active_passage(self, active_passage: PassageDetailDTO | None) -> PassageDetailDTO:
        if active_passage is None:
            raise NoActivePassageError("No active passage is available.")
        return active_passage


def _build_target(view: PsalmLearningViewDTO) -> LearningTargetDTO:
    assert view.active_passage is not None
    active = view.active_passage
    if active.kind is PassageKind.CONSOLIDATION:
        label = "complete Psalm"
    elif active.start_verse == active.end_verse:
        label = f"verse {active.start_verse}"
    else:
        label = f"verses {active.start_verse}-{active.end_verse}"
    token = f"{view.plan.psalm_id}:{active.id}:{view.plan.updated_at.isoformat()}"
    return LearningTargetDTO(token=token, label=label, kind=active.kind)
