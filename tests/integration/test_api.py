from pathlib import Path

from fastapi.testclient import TestClient

from psalter.config import build_config
from psalter.web.app import create_app


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PSALTER_SCRIPTURE_PROVIDER", "mock")
    app = create_app(build_config(data_dir=tmp_path))
    return TestClient(app)


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
