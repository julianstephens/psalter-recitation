from __future__ import annotations

from typing import Protocol

from psalter.application.dto import AudioArtifact, TranscriptArtifact


class Transcriber(Protocol):
    def transcribe(self, artifact: AudioArtifact) -> TranscriptArtifact: ...
