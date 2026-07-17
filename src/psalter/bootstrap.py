from __future__ import annotations

from dataclasses import dataclass

from psalter.adapters.audio.unsupported import UnsupportedAudioRecorder
from psalter.adapters.persistence import (
    SqliteDatabase,
    SqliteLearningSessionRepository,
    SqliteMigrator,
    SqlitePassageRepository,
    SqliteRecitationRepository,
    SqliteReviewRepository,
    migrations_dir,
)
from psalter.adapters.system_clock import SystemClock
from psalter.adapters.transcription.unsupported import UnsupportedTranscriber
from psalter.application.services.learning import LearningService
from psalter.application.services.progress import ProgressService
from psalter.application.services.recitation import RecitationService, UnsupportedAssessmentPolicy
from psalter.application.services.review import ReviewService
from psalter.config import AppConfig, build_config


@dataclass(frozen=True, slots=True)
class Container:
    config: AppConfig
    db: SqliteDatabase
    migrator: SqliteMigrator
    learning_service: LearningService
    recitation_service: RecitationService
    review_service: ReviewService
    progress_service: ProgressService


def build_container(config: AppConfig | None = None) -> Container:
    resolved = config or build_config()
    db = SqliteDatabase(path=resolved.db_path)
    migrator = SqliteMigrator(database=db, migrations_dir=migrations_dir())
    clock = SystemClock()

    passage_repo = SqlitePassageRepository(db)
    learning_repo = SqliteLearningSessionRepository(db)
    recitation_repo = SqliteRecitationRepository(db)
    review_repo = SqliteReviewRepository(db)

    learning_service = LearningService(passages=passage_repo, sessions=learning_repo, clock=clock)
    recitation_service = RecitationService(
        passages=passage_repo,
        sessions=learning_repo,
        attempts=recitation_repo,
        recorder=UnsupportedAudioRecorder(),
        transcriber=UnsupportedTranscriber(),
        assessor=UnsupportedAssessmentPolicy(),
        clock=clock,
    )
    review_service = ReviewService(reviews=review_repo, clock=clock)
    progress_service = ProgressService(
        passages=passage_repo,
        sessions=learning_repo,
        reviews=review_repo,
        clock=clock,
    )

    return Container(
        config=resolved,
        db=db,
        migrator=migrator,
        learning_service=learning_service,
        recitation_service=recitation_service,
        review_service=review_service,
        progress_service=progress_service,
    )


def initialize_storage(config: AppConfig | None = None) -> AppConfig:
    container = build_container(config)
    container.migrator.apply_pending()
    return container.config
