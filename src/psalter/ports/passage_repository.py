from __future__ import annotations

from typing import Protocol

from psalter.domain.passage import Passage


class PassageRepository(Protocol):
    def add(self, passage: Passage) -> None: ...

    def get_by_id(self, passage_id: str) -> Passage | None: ...

    def list_all(self) -> list[Passage]: ...

    def count_all(self) -> int: ...
