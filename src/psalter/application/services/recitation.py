from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from psalter.application.errors import NotFoundError, NotSupportedError
from psalter.domain.learning import LearningPhase
from psalter.domain.recitation import RecitationAttempt, RecitationResult
from psalter.ports.audio_recorder import AudioRecorder
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.recitation_repository import RecitationRepository
from psalter.ports.transcriber import Transcriber


class TranscriptAssessor(Protocol):
    def assess(
        self, canonical_text: str, normalized_transcript: str
    ) -> tuple[RecitationResult, float]: ...


class UnsupportedAssessmentPolicy:
    def assess(
        self, canonical_text: str, normalized_transcript: str
    ) -> tuple[RecitationResult, float]:
        raise NotSupportedError(
            "No transcript assessment policy has been configured. "
            "Textual assessment is not implemented in this scaffold."
        )


@dataclass(frozen=True, slots=True)
class RecitationAttemptDTO:
    id: str
    passage_id: str
    result: RecitationResult
    accuracy: float


class RecitationService:
    def __init__(
        self,
        passages: PassageRepository,
        sessions: LearningRepository,
        attempts: RecitationRepository,
        recorder: AudioRecorder,
        transcriber: Transcriber,
        assessor: TranscriptAssessor,
        clock: Clock,
    ) -> None:
        self._passages = passages
        self._sessions = sessions
        self._attempts = attempts
        self._recorder = recorder
        self._transcriber = transcriber
        self._assessor = assessor
        self._clock = clock

    def record_and_assess(self, passage_id: str) -> RecitationAttemptDTO:
        passage = self._passages.get_by_id(passage_id)
        if passage is None:
            raise NotFoundError(f"Passage not found: {passage_id}")

        session = self._sessions.get_latest_by_passage(passage_id)
        if session is None:
            raise NotFoundError(f"Learning session not found for passage: {passage_id}")

        artifact = self._recorder.record(passage_id)
        transcript = self._transcriber.transcribe(artifact)
        result, accuracy = self._assessor.assess(
            canonical_text=passage.canonical_text,
            normalized_transcript=transcript.normalized_transcript,
        )

        attempt = RecitationAttempt(
            id=str(uuid4()),
            passage_id=passage_id,
            attempted_at=self._clock.now(),
            transcript=transcript.transcript,
            normalized_transcript=transcript.normalized_transcript,
            result=result,
            accuracy=accuracy,
        )
        self._attempts.add(attempt)

        if session.phase is LearningPhase.READY_FOR_RECITATION:
            if result is RecitationResult.PASS:
                self._sessions.upsert(session.mark_learned(self._clock.now()))
            elif result is RecitationResult.RETRY:
                self._sessions.upsert(session.mark_needs_reinforcement())

        return RecitationAttemptDTO(
            id=attempt.id,
            passage_id=attempt.passage_id,
            result=attempt.result,
            accuracy=attempt.accuracy,
        )
