from __future__ import annotations

from datetime import datetime
from typing import Protocol

from psalter.domain.review import ReviewState


class ReviewRepository(Protocol):
    def list_due(self, now: datetime) -> list[ReviewState]: ...
