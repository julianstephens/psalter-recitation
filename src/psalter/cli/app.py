from __future__ import annotations

from typing import Annotated

import typer

from psalter.cli.commands import (
    register_init,
    register_learn,
    register_passage,
    register_progress,
    register_psalm,
    register_review,
    register_settings,
)
from psalter.config import build_config
from psalter.logging import configure_logging, debug_event, get_logger

logger = get_logger(__name__)
app = typer.Typer(help="CLI for Psalm memorization workflow scaffolding")


@app.callback()
def configure_app(
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable application debug logging on stderr."),
    ] = False,
    log_level: Annotated[
        str | None,
        typer.Option("--log-level", help="Override PSALTER_LOG_LEVEL for this invocation."),
    ] = None,
) -> None:
    config = build_config()
    resolved_level = "DEBUG" if debug else (log_level or config.log_level)
    configure_logging(resolved_level)
    debug_event(
        logger,
        "application_started",
        log_level=resolved_level.upper(),
        data_dir=str(config.data_dir),
    )


register_init(app)
register_psalm(app)
register_passage(app)
register_learn(app)
register_review(app)
register_progress(app)
register_settings(app)


def run() -> None:
    app()
