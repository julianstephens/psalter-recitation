from __future__ import annotations

from datetime import datetime
from typing import Protocol

from psalter.domain.review import ReviewState


class ReviewRepository(Protocol):
    def get_by_passage(self, passage_id: str) -> ReviewState | None: ...

    def upsert(self, state: ReviewState) -> None: ...

    def list_due(self, now: datetime) -> list[ReviewState]: ...
