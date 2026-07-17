from pathlib import Path

from psalter.adapters.persistence.sqlite import (
    SqliteDatabase,
    SqliteLearningSessionRepository,
    SqliteMigrator,
    SqlitePassageRepository,
    SqliteRecitationCommitter,
    SqliteRecitationRepository,
    SqliteReviewRepository,
)

__all__ = [
    "SqliteDatabase",
    "SqliteLearningSessionRepository",
    "SqliteMigrator",
    "SqlitePassageRepository",
    "SqliteRecitationCommitter",
    "SqliteRecitationRepository",
    "SqliteReviewRepository",
    "migrations_dir",
]


def migrations_dir() -> Path:
    return Path(__file__).with_name("migrations")
