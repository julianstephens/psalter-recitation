from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    data_dir: Path
    db_path: Path


def default_data_dir() -> Path:
    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "psalter-recitation"
    return Path.home() / ".local" / "share" / "psalter-recitation"


def build_config(data_dir: Path | None = None) -> AppConfig:
    root = data_dir or default_data_dir()
    return AppConfig(data_dir=root, db_path=root / "psalter.db")
