from __future__ import annotations

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

app = typer.Typer(help="CLI for Psalm memorization workflow scaffolding")

register_init(app)
register_psalm(app)
register_passage(app)
register_learn(app)
register_review(app)
register_progress(app)
register_settings(app)


def run() -> None:
    app()
