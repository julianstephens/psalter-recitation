from __future__ import annotations

from typing import Protocol

from psalter.application.dto import AudioArtifact, TranscriptDTO


class Transcriber(Protocol):
    def transcribe(self, artifact: AudioArtifact) -> TranscriptDTO: ...
