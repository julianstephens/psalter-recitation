from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from psalter.application.dto import LearningSessionDTO, PassageDTO
from psalter.application.errors import NotFoundError
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

    def begin_or_resume(self, passage_id: str) -> LearningSessionDTO:
        if self._passages.get_by_id(passage_id) is None:
            raise NotFoundError(f"Passage not found: {passage_id}")

        session = self._sessions.get_latest_by_passage(passage_id)
        if session is None:
            session = LearningSession(
                id=str(uuid4()),
                passage_id=passage_id,
                phase=LearningPhase.UNSEEN,
                practice_level=0,
                successful_blank_recitations=0,
                started_at=self._clock.now(),
                completed_at=None,
            ).begin_exposure()
            self._sessions.upsert(session)
            return _to_dto(session)

        return _to_dto(session)

    def complete_exposure(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        updated = session.complete_exposure()
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def advance_practice_ready(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        updated = session.mark_practice_ready()
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def set_phase(self, passage_id: str, phase: LearningPhase) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        updated = replace(session, phase=phase)
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def get_current_session(self, passage_id: str) -> LearningSessionDTO | None:
        session = self._sessions.get_latest_by_passage(passage_id)
        return _to_dto(session) if session else None

    def get_passage(self, passage_id: str) -> PassageDTO:
        passage = self._passages.get_by_id(passage_id)
        if passage is None:
            raise NotFoundError(f"Passage not found: {passage_id}")
        return PassageDTO(
            id=passage.id,
            translation_id=passage.translation_id,
            psalm_number=passage.psalm_number,
            start_verse=passage.start_verse,
            end_verse=passage.end_verse,
        )

    def mark_learned(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        updated = session.mark_learned(self._clock.now())
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def mark_needs_reinforcement(self, passage_id: str) -> LearningSessionDTO:
        session = self._require_session(passage_id)
        updated = session.mark_needs_reinforcement()
        self._sessions.upsert(updated)
        return _to_dto(updated)

    def _require_session(self, passage_id: str) -> LearningSession:
        session = self._sessions.get_latest_by_passage(passage_id)
        if session is None:
            raise NotFoundError(f"Learning session not found for passage: {passage_id}")
        return session


def _to_dto(session: LearningSession) -> LearningSessionDTO:
    return LearningSessionDTO(
        id=session.id,
        passage_id=session.passage_id,
        phase=session.phase,
        practice_level=session.practice_level,
        successful_blank_recitations=session.successful_blank_recitations,
        started_at=session.started_at,
        completed_at=session.completed_at,
    )
