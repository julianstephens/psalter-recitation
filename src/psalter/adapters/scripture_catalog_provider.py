from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from psalter.application.errors import (
    PsalmDownloadFailedError,
    PsalmPayloadInvalidError,
    ScriptureProviderUnavailableError,
    TranslationCatalogUnavailableError,
)
from psalter.ports.scripture_catalog_provider import (
    ImportedPsalm,
    ImportedPsalmVerse,
    ScriptureCatalogProvider,
    TranslationInfo,
)


@dataclass(frozen=True, slots=True)
class HelloAoScriptureCatalogProvider(ScriptureCatalogProvider):
    base_url: str
    timeout_seconds: float = 20.0

    def list_translations(self) -> tuple[TranslationInfo, ...]:
        endpoints = (
            "/translations.json",
            "/translations",
            "/catalog/translations",
        )
        last_error: Exception | None = None
        for endpoint in endpoints:
            try:
                payload = self._fetch_json(endpoint)
                return _parse_translations(payload)
            except (
                TranslationCatalogUnavailableError,
                ScriptureProviderUnavailableError,
                PsalmPayloadInvalidError,
            ) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise TranslationCatalogUnavailableError("Translation catalog was unavailable.")

    def fetch_psalm(self, translation_id: str, psalm_number: int) -> ImportedPsalm:
        path = f"/{quote(translation_id)}/PSA/{psalm_number}.json"
        try:
            payload = self._fetch_json(path)
        except (ScriptureProviderUnavailableError, TranslationCatalogUnavailableError) as exc:
            raise PsalmDownloadFailedError(
                f"Failed to import Psalm {psalm_number} from {translation_id}: {exc}"
            ) from exc
        return _parse_psalm_payload(
            translation_id=translation_id, psalm_number=psalm_number, payload=payload
        )

    def _fetch_json(self, path: str) -> object:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if int(status) >= 400:
                    raise TranslationCatalogUnavailableError(
                        f"Scripture provider returned HTTP {status}."
                    )
                return json.loads(response.read().decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TranslationCatalogUnavailableError(
                "Scripture provider returned invalid JSON."
            ) from exc
        except HTTPError as exc:
            raise TranslationCatalogUnavailableError(
                f"Scripture provider returned HTTP {exc.code}."
            ) from exc
        except URLError as exc:
            raise ScriptureProviderUnavailableError(
                f"Scripture provider unavailable: {exc.reason}"
            ) from exc


@dataclass(frozen=True, slots=True)
class MockScriptureCatalogProvider(ScriptureCatalogProvider):
    def list_translations(self) -> tuple[TranslationInfo, ...]:
        return (
            TranslationInfo(
                id="BSB", name="Berean Standard Bible", language="en", supports_psalms=True
            ),
            TranslationInfo(
                id="KJV", name="King James Version", language="en", supports_psalms=True
            ),
            TranslationInfo(
                id="WEB", name="World English Bible", language="en", supports_psalms=True
            ),
        )

    def fetch_psalm(self, translation_id: str, psalm_number: int) -> ImportedPsalm:
        verses = tuple(
            ImportedPsalmVerse(
                verse_number=index,
                canonical_text=f"{translation_id} Psalm {psalm_number}:{index}",
            )
            for index in range(1, 4)
        )
        return ImportedPsalm(
            translation_id=translation_id, psalm_number=psalm_number, verses=verses
        )


def _parse_translations(payload: object) -> tuple[TranslationInfo, ...]:
    if isinstance(payload, dict):
        candidates = payload.get("translations", payload.get("data"))
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise PsalmPayloadInvalidError("Translation catalog payload was invalid.")
    parsed: list[TranslationInfo] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        translation_id = item.get("id", item.get("translation_id"))
        name = item.get("name", item.get("display_name", translation_id))
        if not isinstance(translation_id, str) or not isinstance(name, str):
            continue
        language = item.get("language")
        supports_psalms = item.get("supports_psalms", True)
        parsed.append(
            TranslationInfo(
                id=translation_id,
                name=name,
                language=language if isinstance(language, str) else "unknown",
                supports_psalms=bool(supports_psalms),
            )
        )
    if not parsed:
        raise TranslationCatalogUnavailableError("No supported translations were returned.")
    return tuple(parsed)


def _parse_psalm_payload(
    *, translation_id: str, psalm_number: int, payload: object
) -> ImportedPsalm:
    if not isinstance(payload, dict):
        raise PsalmPayloadInvalidError(
            f"Failed to import Psalm {psalm_number} from {translation_id}: "
            "payload must be an object."
        )
    chapter = payload.get("chapter")
    if not isinstance(chapter, dict):
        raise PsalmPayloadInvalidError(
            f"Failed to import Psalm {psalm_number} from {translation_id}: missing chapter data."
        )
    content = chapter.get("content")
    if not isinstance(content, list):
        raise PsalmPayloadInvalidError(
            f"Failed to import Psalm {psalm_number} from {translation_id}: missing verse data."
        )
    verses: list[ImportedPsalmVerse] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "verse":
            continue
        number = item.get("number")
        chunks = item.get("content")
        if not isinstance(number, int) or not isinstance(chunks, list):
            raise PsalmPayloadInvalidError(
                f"Failed to import Psalm {psalm_number} from {translation_id}: "
                "malformed verse data."
            )
        text = _normalize_rendered_text(_render_verse_content(chunks))
        if not text:
            raise PsalmPayloadInvalidError(
                f"Failed to import Psalm {psalm_number} from {translation_id}: "
                f"verse {number} was blank."
            )
        verses.append(ImportedPsalmVerse(verse_number=number, canonical_text=text))
    if not verses:
        raise PsalmPayloadInvalidError(
            f"Failed to import Psalm {psalm_number} from {translation_id}: no verses were returned."
        )
    expected = list(range(1, len(verses) + 1))
    actual = [item.verse_number for item in verses]
    if actual != expected:
        raise PsalmPayloadInvalidError(
            f"Failed to import Psalm {psalm_number} from {translation_id}: "
            "verses must be contiguous."
        )
    return ImportedPsalm(
        translation_id=translation_id, psalm_number=psalm_number, verses=tuple(verses)
    )


def _render_verse_content(chunks: list[object]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, str):
            parts.append(chunk)
            continue
        if not isinstance(chunk, dict):
            continue
        text = chunk.get("text")
        if isinstance(text, str):
            parts.append(text)
            continue
        heading = chunk.get("heading")
        if isinstance(heading, str):
            parts.append(heading)
            continue
        if chunk.get("lineBreak") is True:
            parts.append("\n")
    return "".join(parts)


def _normalize_rendered_text(text: str) -> str:
    compact_lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in compact_lines if line).strip()
