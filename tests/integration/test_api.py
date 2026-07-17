from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from psalter.application.dto import RecitationAssessmentDTO
from psalter.config import build_config
from psalter.domain.recitation import RecitationResult, RecitationSource
from psalter.web.app import create_app


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PSALTER_SCRIPTURE_PROVIDER", "mock")
    app = create_app(build_config(data_dir=tmp_path))
    return TestClient(app)


class _FakeUploadedSpokenService:
    def prepare_transcribe_and_submit_uploaded(
        self,
        *,
        passage_id: str,
        source: object,
        content_type: str,
    ) -> RecitationAssessmentDTO:
        return RecitationAssessmentDTO(
            attempt_id="audio-attempt",
            passage_id=passage_id,
            learning_session_id="session-1",
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


def test_health_and_readiness_before_init(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        readiness = client.get("/api/v1/readiness")
        assert readiness.status_code == 200
        readiness_payload = readiness.json()
        assert readiness_payload["storage_ready"] is True
        assert readiness_payload["installation"]["catalog_status"] == "not_started"

        progress = client.get("/api/v1/progress")
        assert progress.status_code == 409
        assert progress.headers["X-Request-ID"] == progress.json()["error"]["request_id"]
        assert progress.json()["error"]["code"] == "installation_not_ready"


def test_installation_and_read_only_api_surface(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        translations = client.get("/api/v1/translations")
        assert translations.status_code == 200
        assert {item["id"] for item in translations.json()["items"]} >= {"BSB", "KJV"}

        install = client.post("/api/v1/installation", json={"translation_id": "BSB"})
        assert install.status_code == 200
        install_payload = install.json()
        assert install_payload["catalog_status"] == "ready"
        assert install_payload["default_translation_id"] == "BSB"
        assert install_payload["result"]["imported_psalm_count"] == 150

        installation = client.get("/api/v1/installation")
        assert installation.status_code == 200
        assert installation.json()["is_ready"] is True

        settings = client.get("/api/v1/settings")
        assert settings.status_code == 200
        assert settings.json()["default_translation_id"] == "BSB"

        psalms = client.get("/api/v1/psalms")
        assert psalms.status_code == 200
        assert len(psalms.json()["items"]) == 150

        psalm = client.get("/api/v1/psalms/90")
        assert psalm.status_code == 200
        psalm_payload = psalm.json()
        assert psalm_payload["translation_id"] == "BSB"
        assert "BSB Psalm 90:1" in psalm_payload["canonical_text"]
        assert psalm_payload["learning"]["status"] == "learning_sections"

        progress = client.get("/api/v1/progress")
        assert progress.status_code == 200
        progress_payload = progress.json()
        assert progress_payload["summary"]["total_passages"] > 0
        assert len(progress_payload["psalms"]) == 150

        reviews = client.get("/api/v1/reviews")
        assert reviews.status_code == 200
        assert reviews.json()["items"] == []


def test_learning_workflow_api_supports_typed_progression(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        install = client.post("/api/v1/installation", json={"translation_id": "BSB"})
        assert install.status_code == 200

        start = client.post("/api/v1/psalms/1/learning/start", json={})
        assert start.status_code == 200
        start_payload = start.json()
        assert start_payload["screen"] == "exposure"
        assert start_payload["active_target"] is not None

        exposure = client.post(
            "/api/v1/psalms/1/learning/exposure/complete",
            json={"target_token": start_payload["active_target"]["token"]},
        )
        assert exposure.status_code == 200
        practice_payload = exposure.json()
        assert practice_payload["screen"] == "practice"

        current = practice_payload
        for _ in range(5):
            current = client.post(
                "/api/v1/psalms/1/learning/practice/complete",
                json={"target_token": current["active_target"]["token"]},
            ).json()
        assert current["screen"] == "ready_for_recitation"

        first_recitation = client.post(
            "/api/v1/psalms/1/learning/recitations/text",
            json={
                "target_token": current["active_target"]["token"],
                "text": "bsb psalm 1:1\nbsb psalm 1:2\nbsb psalm 1:3",
            },
        )
        assert first_recitation.status_code == 200
        first_payload = first_recitation.json()
        assert first_payload["assessment"]["result"] == "pass"
        assert first_payload["assessment"]["remaining_successes_required"] == 1

        second_recitation = client.post(
            "/api/v1/psalms/1/learning/recitations/text",
            json={
                "target_token": first_payload["active_target"]["token"],
                "text": "bsb psalm 1:1\nbsb psalm 1:2\nbsb psalm 1:3",
            },
        )
        assert second_recitation.status_code == 200
        second_payload = second_recitation.json()
        assert second_payload["assessment"]["result"] == "pass"
        assert second_payload["assessment"]["remaining_successes_required"] == 0
        assert second_payload["screen"] in {
            "section_completed",
            "consolidation_started",
            "psalm_completed",
        }


def test_learning_workflow_api_accepts_audio_upload(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        install = client.post("/api/v1/installation", json={"translation_id": "BSB"})
        assert install.status_code == 200

        client.app.state.container = replace(
            client.app.state.container,
            spoken_recitation_service=_FakeUploadedSpokenService(),
        )

        start = client.post("/api/v1/psalms/1/learning/start", json={})
        assert start.status_code == 200

        exposure = client.post(
            "/api/v1/psalms/1/learning/exposure/complete",
            json={"target_token": start.json()["active_target"]["token"]},
        )
        current = exposure.json()
        for _ in range(5):
            current = client.post(
                "/api/v1/psalms/1/learning/practice/complete",
                json={"target_token": current["active_target"]["token"]},
            ).json()

        audio = client.post(
            "/api/v1/psalms/1/learning/recitations/audio",
            data={"target_token": current["active_target"]["token"]},
            files={"audio": ("sample.webm", b"fake-audio", "audio/webm")},
        )
        assert audio.status_code == 200
        payload = audio.json()
        assert payload["assessment"]["result"] == "pass"
        assert payload["assessment"]["remaining_successes_required"] == 1
