from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from psalter.application.dto import AudioArtifact, TranscriptDTO
from psalter.application.services.recitation import RecitationService, TranscriptAssessor
from psalter.domain.learning import LearningPhase, LearningSession
from psalter.domain.passage import Passage
from psalter.domain.recitation import RecitationAttempt, RecitationResult


@dataclass
class FakeClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


class FakePassages:
    def __init__(self, passage: Passage) -> None:
        self._passage = passage

    def get_by_id(self, passage_id: str) -> Passage | None:
        return self._passage if self._passage.id == passage_id else None

    def count_all(self) -> int:
        return 1


class FakeSessions:
    def __init__(self, session: LearningSession) -> None:
        self.session = session

    def get_latest_by_passage(self, passage_id: str) -> LearningSession | None:
        return self.session if self.session.passage_id == passage_id else None

    def upsert(self, session: LearningSession) -> None:
        self.session = session

    def count_by_phase(self, phase: LearningPhase) -> int:
        return 1 if self.session.phase is phase else 0


class FakeAttempts:
    def __init__(self) -> None:
        self.items: list[RecitationAttempt] = []

    def add(self, attempt: RecitationAttempt) -> None:
        self.items.append(attempt)


class FakeRecorder:
    def record(self, passage_id: str) -> AudioArtifact:
        return AudioArtifact(uri=f"file:///tmp/{passage_id}.wav")


class FakeTranscriber:
    def transcribe(self, artifact: AudioArtifact) -> TranscriptDTO:
        return TranscriptDTO(transcript="text", normalized_transcript="text")


class PassAssessor(TranscriptAssessor):
    def assess(
        self, canonical_text: str, normalized_transcript: str
    ) -> tuple[RecitationResult, float]:
        return (RecitationResult.PASS, 1.0)


class RetryAssessor(TranscriptAssessor):
    def assess(
        self, canonical_text: str, normalized_transcript: str
    ) -> tuple[RecitationResult, float]:
        return (RecitationResult.RETRY, 0.4)


def _ready_session() -> LearningSession:
    return LearningSession(
        id="s1",
        passage_id="p1",
        phase=LearningPhase.READY_FOR_RECITATION,
        practice_level=0,
        successful_blank_recitations=0,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=None,
    )


def _passage() -> Passage:
    return Passage(
        id="p1",
        translation_id="esv",
        psalm_number=1,
        start_verse=1,
        end_verse=1,
        canonical_text="Blessed",
    )


def test_passing_recitation_moves_ready_session_to_learned() -> None:
    sessions = FakeSessions(_ready_session())
    service = RecitationService(
        passages=FakePassages(_passage()),
        sessions=sessions,
        attempts=FakeAttempts(),
        recorder=FakeRecorder(),
        transcriber=FakeTranscriber(),
        assessor=PassAssessor(),
        clock=FakeClock(datetime(2026, 1, 2, tzinfo=UTC)),
    )

    service.record_and_assess("p1")
    assert sessions.session.phase is LearningPhase.LEARNED


def test_failed_recitation_does_not_mark_passage_learned() -> None:
    sessions = FakeSessions(_ready_session())
    service = RecitationService(
        passages=FakePassages(_passage()),
        sessions=sessions,
        attempts=FakeAttempts(),
        recorder=FakeRecorder(),
        transcriber=FakeTranscriber(),
        assessor=RetryAssessor(),
        clock=FakeClock(datetime(2026, 1, 2, tzinfo=UTC)),
    )

    service.record_and_assess("p1")
    assert sessions.session.phase is not LearningPhase.LEARNED
