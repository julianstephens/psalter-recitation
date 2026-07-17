from __future__ import annotations

from uuid import uuid4

from psalter.application.dto import (
    LearningSessionDTO,
    LearningViewDTO,
    PassageDetailDTO,
    PassageSummaryDTO,
    PracticeViewDTO,
)
from psalter.application.errors import (
    InvalidLearningTransitionError,
    LearningSessionNotFoundError,
    PassageNotFoundError,
)
from psalter.application.services.masking import mask_text
from psalter.domain.errors import InvalidTransitionError
from psalter.domain.learning import LearningPhase, LearningSession
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository


class LearningService:
    def __init__(
        self,
        passages: PassageRepository,
        sessions: LearningRepository,
        clock: Clock,
    ) -> None:
        self._passages = passages
        self._sessions = sessions
        self._clock = clock
        self._max_practice_level = 4

    def begin_or_resume(self, passage_id: str) -> LearningSessionDTO:
        if self._passages.get_by_id(passage_id) is None:
            raise PassageNotFoundError(f"Passage not found: {passage_id}")

        session = self._sessions.get_by_passage(passage_id)
        if session is None:
            now = self._clock.now()
            session = LearningSession(
                id=str(uuid4()),
                passage_id=passage_id,
                phase=LearningPhase.UNSEEN,
                practice_level=0,
                successful_blank_recitations=0,
                started_at=now,
                updated_at=now,
                completed_at=None,
            ).begin_exposure(now)
            self._sessions.upsert(session)
            return _to_dto(session)

        return _to_dto(session)

    def complete_exposure(self, passage_id: str) -> LearningSessionDTO:
        return self._complete_exposure(passage_id, skip_practice=False)

    def complete_exposure_and_mark_ready(self, passage_id: str) -> LearningSessionDTO:
        return self._complete_exposure(passage_id, skip_practice=True)

    def _complete_exposure(self, passage_id: str, *, skip_practice: bool) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        try:
            updated = session.complete_exposure(
                self._clock.now(),
                skip_practice=skip_practice,
            )
        except InvalidTransitionError as exc:
            raise InvalidLearningTransitionError(str(exc)) from exc
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def complete_practice_level(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        now = self._clock.now()
        try:
            if session.practice_level >= self._max_practice_level:
                updated = session.mark_practice_ready(now)
            else:
                updated = session.advance_practice_level(self._max_practice_level + 1, now)
        except InvalidTransitionError as exc:
            raise InvalidLearningTransitionError(str(exc)) from exc
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def resume_reinforcement(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        try:
            updated = session.resume_practice(self._clock.now())
        except InvalidTransitionError as exc:
            raise InvalidLearningTransitionError(str(exc)) from exc
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def get_current_session(self, passage_id: str) -> LearningSessionDTO | None:
        session = self._sessions.get_by_passage(passage_id)
        return _to_dto(session) if session else None

    def get_passage(self, passage_id: str) -> PassageDetailDTO:
        passage = self._passages.get_by_id(passage_id)
        if passage is None:
            raise PassageNotFoundError(f"Passage not found: {passage_id}")
        return PassageDetailDTO(
            id=passage.id,
            psalm_id=passage.psalm_id,
            translation_id=passage.translation_id,
            psalm_number=passage.psalm_number,
            start_verse=passage.start_verse,
            end_verse=passage.end_verse,
            canonical_text=passage.canonical_text,
            sequence_number=passage.sequence_number,
            kind=passage.kind,
            segmentation_policy_version=passage.segmentation_policy_version,
        )

    def get_passage_summaries(self) -> list[PassageSummaryDTO]:
        return [
            PassageSummaryDTO(
                id=item.id,
                psalm_id=item.psalm_id,
                translation_id=item.translation_id,
                psalm_number=item.psalm_number,
                start_verse=item.start_verse,
                end_verse=item.end_verse,
                sequence_number=item.sequence_number,
                kind=item.kind,
            )
            for item in self._passages.list_all()
        ]

    def get_learning_view(self, passage_id: str) -> LearningViewDTO:
        passage = self.get_passage(passage_id)
        session = self._require_session(passage_id)
        return LearningViewDTO(passage=passage, session=_to_dto(session))

    def get_practice_view(self, passage_id: str) -> PracticeViewDTO:
        view = self.get_learning_view(passage_id)
        return PracticeViewDTO(
            session=view.session,
            masked_text=mask_text(
                canonical_text=view.passage.canonical_text,
                passage_id=passage_id,
                level=view.session.practice_level,
            ),
            level=view.session.practice_level,
            max_level=self._max_practice_level,
        )

    def _require_session(self, passage_id: str) -> LearningSession:
        session = self._sessions.get_by_passage(passage_id)
        if session is None:
            raise LearningSessionNotFoundError(
                f"Learning session not found for passage: {passage_id}"
            )
        return session


def _to_dto(session: LearningSession) -> LearningSessionDTO:
    return LearningSessionDTO(
        id=session.id,
        passage_id=session.passage_id,
        phase=session.phase,
        practice_level=session.practice_level,
        successful_blank_recitations=session.successful_blank_recitations,
        started_at=session.started_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
    )
