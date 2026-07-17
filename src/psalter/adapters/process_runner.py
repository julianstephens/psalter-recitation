from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from psalter.application.errors import WhisperProcessFailedError


@dataclass(frozen=True, slots=True)
class ProcessResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: float | None = None,
) -> ProcessResult:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            shell=False,
            cwd=cwd,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WhisperProcessFailedError(
            f"Process timed out after {timeout_seconds}s: {' '.join(args)}"
        ) from exc
    return ProcessResult(
        args=tuple(args),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
