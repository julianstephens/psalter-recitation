from __future__ import annotations

from typing import Protocol

from psalter.domain.learning import LearningPhase, LearningSession


class LearningRepository(Protocol):
    def get_by_passage(self, passage_id: str) -> LearningSession | None: ...

    def upsert(self, session: LearningSession) -> None: ...

    def count_all(self) -> int: ...

    def count_by_phase(self, phase: LearningPhase) -> int: ...
