from __future__ import annotations

import pytest

from psalter.adapters.scripture_catalog_provider import HelloAoScriptureCatalogProvider
from psalter.application.errors import TranslationCatalogUnavailableError


class _FakeResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def test_list_translations_maps_invalid_json_to_catalog_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = HelloAoScriptureCatalogProvider(
        base_url="https://example.invalid",
        timeout_seconds=1,
    )

    def _fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(b"")

    monkeypatch.setattr("psalter.adapters.scripture_catalog_provider.urlopen", _fake_urlopen)

    with pytest.raises(TranslationCatalogUnavailableError) as exc:
        provider.list_translations()
    assert "invalid JSON" in str(exc.value)
