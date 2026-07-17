from __future__ import annotations

from typing import Protocol

from psalter.domain.passage import Passage


class PassageRepository(Protocol):
    def get_by_id(self, passage_id: str) -> Passage | None: ...

    def count_all(self) -> int: ...
