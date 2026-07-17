from __future__ import annotations

import io
import logging

import pytest

from psalter.logging import configure_logging, debug_event, get_logger


@pytest.fixture(autouse=True)
def reset_psalter_logger() -> None:
    root = logging.getLogger("psalter")
    previous_handlers = list(root.handlers)
    previous_level = root.level
    previous_propagate = root.propagate
    root.handlers.clear()
    yield
    root.handlers[:] = previous_handlers
    root.setLevel(previous_level)
    root.propagate = previous_propagate


def test_debug_event_emits_sorted_fields_when_debug_enabled() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger("psalter")
    root.addHandler(handler)

    configure_logging("DEBUG", force=True)
    debug_event(get_logger("psalter.test"), "catalog_started", psalm_number=90, translation="BSB")

    rendered = stream.getvalue()
    assert "catalog_started" in rendered
    assert "psalm_number=90" in rendered
    assert "translation='BSB'" in rendered


def test_debug_event_is_silent_at_warning_level() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger("psalter")
    root.addHandler(handler)

    configure_logging("WARNING", force=True)
    debug_event(get_logger("psalter.test"), "hidden_event", value=1)

    assert stream.getvalue() == ""


def test_non_forced_configuration_preserves_cli_override() -> None:
    configure_logging("DEBUG", force=True)
    configure_logging("WARNING")

    assert logging.getLogger("psalter").level == logging.DEBUG


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported log level"):
        configure_logging("verbose", force=True)
