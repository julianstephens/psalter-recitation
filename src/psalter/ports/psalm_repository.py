from __future__ import annotations

from typing import Protocol

from psalter.domain.passage import Passage
from psalter.domain.psalm import Psalm, PsalmLearningPlan


class PsalmRepository(Protocol):
    def add_psalm_bundle(self, psalm: Psalm, passages: tuple[Passage, ...]) -> None: ...

    def get_by_id(self, psalm_id: str) -> Psalm | None: ...

    def get_by_translation_and_number(
        self,
        translation_id: str,
        psalm_number: int,
    ) -> Psalm | None: ...

    def list_by_number(self, psalm_number: int) -> list[Psalm]: ...

    def list_all(self) -> list[Psalm]: ...


class PsalmLearningPlanRepository(Protocol):
    def get_by_psalm_id(self, psalm_id: str) -> PsalmLearningPlan | None: ...

    def upsert(self, plan: PsalmLearningPlan, expected_version: int | None = None) -> None: ...

    def list_all(self) -> list[PsalmLearningPlan]: ...
