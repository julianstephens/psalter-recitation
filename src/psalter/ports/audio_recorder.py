from __future__ import annotations

from typing import Protocol

from psalter.application.dto import AudioArtifact


class AudioRecorder(Protocol):
    def record(self, passage_id: str) -> AudioArtifact: ...
