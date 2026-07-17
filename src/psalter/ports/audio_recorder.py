from __future__ import annotations

from typing import Protocol

from psalter.application.dto import AudioArtifact, AudioRecordingRequest


class AudioRecorder(Protocol):
    def record(self, request: AudioRecordingRequest) -> AudioArtifact: ...
