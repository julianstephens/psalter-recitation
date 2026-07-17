from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from psalter.application.dto import (
    AudioArtifact,
    AudioRecordingRequest,
    RecitationAssessmentDTO,
    RecitationSubmission,
    TranscriptArtifact,
)
from psalter.application.errors import ArtifactCleanupFailedError
from psalter.application.services.spoken_recitation import (
    ArtifactRetentionPolicy,
    SpokenRecitationService,
)
from psalter.domain.recitation import RecitationResult, RecitationSource


@dataclass
class FakeRecorder:
    artifact: AudioArtifact
    calls: list[str]
    should_fail: bool = False

    def record(self, request: AudioRecordingRequest) -> AudioArtifact:
        self.calls.append("record")
        if self.should_fail:
            raise RuntimeError("recording failed")
        return self.artifact


@dataclass
class FakeTranscriber:
    artifact: TranscriptArtifact
    calls: list[str]
    should_fail: bool = False

    def transcribe(self, artifact: AudioArtifact) -> TranscriptArtifact:
        self.calls.append("transcribe")
        if self.should_fail:
            raise RuntimeError("transcription failed")
        return self.artifact


@dataclass
class FakeRecitationService:
    assessment: RecitationAssessmentDTO
    calls: list[str]
    last_submission_source: RecitationSource | None = None

    def submit_text(self, submission: RecitationSubmission) -> RecitationAssessmentDTO:
        self.calls.append("submit")
        self.last_submission_source = submission.source
        return self.assessment


def _assessment() -> RecitationAssessmentDTO:
    return RecitationAssessmentDTO(
        attempt_id="a1",
        passage_id="p1",
        learning_session_id="s1",
        source=RecitationSource.SPEECH_TRANSCRIPT,
        result=RecitationResult.PASS,
        weighted_accuracy=1.0,
        omission_count=0,
        substitution_count=0,
        insertion_count=0,
        longest_omitted_span=0,
        policy_version="v1",
        failure_reasons=(),
        omissions=(),
        substitutions=(),
        insertions=(),
        remaining_successes_required=1,
        issues=(),
    )


def test_spoken_service_records_transcribes_and_submits(tmp_path: Path) -> None:
    audio_path = tmp_path / "recording.wav"
    audio_path.write_bytes(b"wav")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("the lord is my shepherd", encoding="utf-8")

    calls: list[str] = []
    service = SpokenRecitationService(
        recorder=FakeRecorder(
            artifact=AudioArtifact(
                path=audio_path, sample_rate_hz=16000, channels=1, duration_seconds=1.2
            ),
            calls=calls,
        ),
        transcriber=FakeTranscriber(
            artifact=TranscriptArtifact(
                text="the lord is my shepherd",
                provider="whisper.cpp",
                model="m.bin",
                raw_output_path=transcript_path,
            ),
            calls=calls,
        ),
        recitation_service=FakeRecitationService(assessment=_assessment(), calls=calls),
    )

    result = service.record_transcribe_and_submit("p1")

    assert result.result is RecitationResult.PASS
    assert calls == ["record", "transcribe", "submit"]
    assert audio_path.exists() is False
    assert transcript_path.exists() is False


def test_spoken_service_does_not_transcribe_when_recording_fails(tmp_path: Path) -> None:
    calls: list[str] = []
    service = SpokenRecitationService(
        recorder=FakeRecorder(
            artifact=AudioArtifact(
                path=tmp_path / "a.wav", sample_rate_hz=16000, channels=1, duration_seconds=1.0
            ),
            calls=calls,
            should_fail=True,
        ),
        transcriber=FakeTranscriber(
            artifact=TranscriptArtifact("t", "whisper.cpp", "m.bin", None),
            calls=calls,
        ),
        recitation_service=FakeRecitationService(assessment=_assessment(), calls=calls),
    )

    with pytest.raises(RuntimeError, match="recording failed"):
        service.record_transcribe_and_submit("p1")
    assert calls == ["record"]


def test_spoken_service_retains_artifacts_when_configured(tmp_path: Path) -> None:
    audio_path = tmp_path / "recording.wav"
    audio_path.write_bytes(b"wav")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("spoken text", encoding="utf-8")
    calls: list[str] = []
    service = SpokenRecitationService(
        recorder=FakeRecorder(
            artifact=AudioArtifact(
                path=audio_path, sample_rate_hz=16000, channels=1, duration_seconds=1.2
            ),
            calls=calls,
        ),
        transcriber=FakeTranscriber(
            artifact=TranscriptArtifact(
                text="spoken text",
                provider="whisper.cpp",
                model="m.bin",
                raw_output_path=transcript_path,
            ),
            calls=calls,
        ),
        recitation_service=FakeRecitationService(assessment=_assessment(), calls=calls),
        retention_policy=ArtifactRetentionPolicy.RETAIN,
    )

    service.record_transcribe_and_submit("p1")

    assert audio_path.exists()
    assert transcript_path.exists()


def test_spoken_service_raises_cleanup_error_when_no_primary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio_path = tmp_path / "recording.wav"
    audio_path.write_bytes(b"wav")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("spoken text", encoding="utf-8")
    calls: list[str] = []

    original_unlink = Path.unlink

    def _failing_unlink(self: Path, *, missing_ok: bool = False) -> None:
        if self == transcript_path:
            raise OSError("forced unlink failure")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", _failing_unlink)

    service = SpokenRecitationService(
        recorder=FakeRecorder(
            artifact=AudioArtifact(
                path=audio_path, sample_rate_hz=16000, channels=1, duration_seconds=1.2
            ),
            calls=calls,
        ),
        transcriber=FakeTranscriber(
            artifact=TranscriptArtifact(
                text="spoken text",
                provider="whisper.cpp",
                model="m.bin",
                raw_output_path=transcript_path,
            ),
            calls=calls,
        ),
        recitation_service=FakeRecitationService(assessment=_assessment(), calls=calls),
    )

    with pytest.raises(ArtifactCleanupFailedError):
        service.record_transcribe_and_submit("p1")


def test_spoken_service_preserves_primary_failure_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio_path = tmp_path / "recording.wav"
    audio_path.write_bytes(b"wav")
    calls: list[str] = []

    def _always_fail_unlink(self: Path, *, missing_ok: bool = False) -> None:
        raise OSError("forced cleanup error")

    monkeypatch.setattr(Path, "unlink", _always_fail_unlink)
    service = SpokenRecitationService(
        recorder=FakeRecorder(
            artifact=AudioArtifact(
                path=audio_path, sample_rate_hz=16000, channels=1, duration_seconds=1.2
            ),
            calls=calls,
        ),
        transcriber=FakeTranscriber(
            artifact=TranscriptArtifact(
                text="ignored",
                provider="whisper.cpp",
                model="m.bin",
                raw_output_path=None,
            ),
            calls=calls,
            should_fail=True,
        ),
        recitation_service=FakeRecitationService(assessment=_assessment(), calls=calls),
    )

    with pytest.raises(RuntimeError, match="transcription failed"):
        service.record_transcribe_and_submit("p1")
