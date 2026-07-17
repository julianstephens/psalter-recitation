from pathlib import Path

from psalter.adapters.persistence.installation_sqlite import (
    SqliteCatalogImportProgressRepository,
    SqliteInstallationSettingsRepository,
    SqlitePsalmCatalogCommitter,
)
from psalter.adapters.persistence.sqlite import (
    SqliteDatabase,
    SqliteLearningSessionRepository,
    SqliteMigrator,
    SqlitePassageRepository,
    SqlitePsalmLearningPlanRepository,
    SqlitePsalmRepository,
    SqliteRecitationCommitter,
    SqliteRecitationRepository,
    SqliteReviewRepository,
)

__all__ = [
    "SqliteCatalogImportProgressRepository",
    "SqliteDatabase",
    "SqliteInstallationSettingsRepository",
    "SqliteLearningSessionRepository",
    "SqliteMigrator",
    "SqlitePassageRepository",
    "SqlitePsalmCatalogCommitter",
    "SqlitePsalmLearningPlanRepository",
    "SqlitePsalmRepository",
    "SqliteRecitationCommitter",
    "SqliteRecitationRepository",
    "SqliteReviewRepository",
    "migrations_dir",
]


def migrations_dir() -> Path:
    return Path(__file__).with_name("migrations")
