from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Any

_ROOT_LOGGER_NAME = "psalter"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(
    level: str | int = logging.WARNING,
    *,
    force: bool = False,
) -> None:
    """Configure Psalter diagnostics on stderr without duplicating handlers."""
    resolved_level = _resolve_level(level)
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.propagate = False

    if logger.handlers and not force:
        return

    logger.setLevel(resolved_level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(resolved_level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def debug_event(logger: logging.Logger, event: str, **fields: object) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug("%s%s", event, _format_fields(fields))


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    normalized = level.strip().upper()
    resolved = logging.getLevelNamesMapping().get(normalized)
    if resolved is None:
        raise ValueError(f"Unsupported log level: {level}")
    return resolved


def _format_fields(fields: Mapping[str, Any]) -> str:
    if not fields:
        return ""
    rendered = " ".join(f"{key}={value!r}" for key, value in sorted(fields.items()))
    return f" {rendered}"
