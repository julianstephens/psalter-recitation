from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO

from psalter.application.dto import (
    AudioArtifact,
    AudioRecordingRequest,
    RecitationAssessmentDTO,
    RecitationSubmission,
)
from psalter.application.errors import (
    ArtifactCleanupFailedError,
    AudioRecorderNotConfiguredError,
    TranscriptEmptyError,
)
from psalter.application.services.recitation import RecitationService
from psalter.domain.recitation import RecitationSource
from psalter.ports.audio_recorder import AudioRecorder
from psalter.ports.transcriber import Transcriber
from psalter.ports.uploaded_audio_preparer import UploadedAudioPreparer

_AUDIO_SAMPLE_RATE = 16_000
_AUDIO_CHANNELS = 1


class ArtifactRetentionPolicy(StrEnum):
    DELETE = "delete"
    RETAIN = "retain"


@dataclass(frozen=True, slots=True)
class SpokenRecitationService:
    recorder: AudioRecorder
    transcriber: Transcriber
    recitation_service: RecitationService
    retention_policy: ArtifactRetentionPolicy = ArtifactRetentionPolicy.DELETE
    uploaded_audio_preparer: UploadedAudioPreparer | None = None

    def record_transcribe_and_submit(
        self,
        passage_id: str,
        *,
        wait_for_stop: Callable[[float | None], bool] | None = None,
        before_transcribe: Callable[[], None] | None = None,
    ) -> RecitationAssessmentDTO:
        return self._transcribe_and_submit(
            passage_id=passage_id,
            audio_factory=lambda: self.recorder.record(
                AudioRecordingRequest(
                    passage_id=passage_id,
                    sample_rate_hz=_AUDIO_SAMPLE_RATE,
                    channels=_AUDIO_CHANNELS,
                    wait_for_stop=wait_for_stop or _wait_for_enter,
                )
            ),
            before_transcribe=before_transcribe,
        )

    def prepare_transcribe_and_submit_uploaded(
        self,
        *,
        passage_id: str,
        source: BinaryIO,
        content_type: str,
    ) -> RecitationAssessmentDTO:
        if self.uploaded_audio_preparer is None:
            raise AudioRecorderNotConfiguredError(
                "Spoken recitation upload is not configured: ffmpeg executable is required."
            )
        prepared = self.uploaded_audio_preparer.prepare(
            passage_id=passage_id,
            source=source,
            content_type=content_type,
        )
        return self._transcribe_and_submit(
            passage_id=passage_id,
            audio_factory=lambda: prepared.artifact,
            cleanup_paths=prepared.cleanup_paths,
        )

    def _transcribe_and_submit(
        self,
        *,
        passage_id: str,
        audio_factory: Callable[[], AudioArtifact],
        cleanup_paths: tuple[Path, ...] = (),
        before_transcribe: Callable[[], None] | None = None,
    ) -> RecitationAssessmentDTO:
        audio_artifact_path: Path | None = None
        transcript_artifact_path: Path | None = None
        try:
            audio = audio_factory()
            audio_artifact_path = audio.path
            if before_transcribe is not None:
                before_transcribe()
            transcript = self.transcriber.transcribe(audio)
            transcript_artifact_path = transcript.raw_output_path
            if not transcript.text.strip():
                raise TranscriptEmptyError("Transcript output is empty.")
            return self.recitation_service.submit_text(
                RecitationSubmission(
                    passage_id=passage_id,
                    source=RecitationSource.SPEECH_TRANSCRIPT,
                    text=transcript.text.strip(),
                )
            )
        finally:
            if self.retention_policy is not ArtifactRetentionPolicy.RETAIN:
                cleanup_errors: list[str] = []
                seen_paths: set[Path] = set()
                for path in (*cleanup_paths, audio_artifact_path, transcript_artifact_path):
                    if path is None:
                        continue
                    if path in seen_paths:
                        continue
                    seen_paths.add(path)
                    try:
                        path.unlink(missing_ok=True)
                    except OSError as exc:
                        cleanup_errors.append(f"{path}: {exc}")
                if cleanup_errors and sys.exc_info()[0] is None:
                    raise ArtifactCleanupFailedError(
                        "Failed to clean temporary artifacts: " + "; ".join(cleanup_errors)
                    )


def _wait_for_enter(timeout: float | None = None) -> bool:
    if timeout is None:
        input()
        return True
    time.sleep(timeout)
    return False
