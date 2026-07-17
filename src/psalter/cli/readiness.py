from __future__ import annotations

import typer

from psalter.application.errors import ApplicationError
from psalter.bootstrap import Container


def require_ready(container: Container) -> None:
    try:
        container.installation_readiness.require_ready()
    except ApplicationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
