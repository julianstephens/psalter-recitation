from __future__ import annotations

from typing import Protocol

from psalter.domain.recitation import RecitationAttempt


class RecitationRepository(Protocol):
    def add(self, attempt: RecitationAttempt) -> None: ...
