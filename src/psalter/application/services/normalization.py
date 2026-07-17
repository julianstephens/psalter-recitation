from __future__ import annotations

import re
import unicodedata

_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u00b4": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
    }
)
_TOKEN_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)


def normalize_tokens(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).translate(_APOSTROPHE_TRANSLATION).casefold()
    tokens: list[str] = []
    for raw in _TOKEN_PATTERN.findall(normalized):
        token = raw.strip("'").replace("'", "")
        if not token:
            continue
        if token.isdigit():
            continue
        tokens.append(token)
    return tuple(tokens)


def normalize_text(text: str) -> str:
    return " ".join(normalize_tokens(text))


def normalize_lines(text: str) -> tuple[tuple[str, ...], ...]:
    return tuple(normalize_tokens(line) for line in text.splitlines())
