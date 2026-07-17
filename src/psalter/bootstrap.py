from __future__ import annotations

from dataclasses import dataclass

from psalter.adapters.audio import FfmpegAudioRecorder, UnsupportedAudioRecorder
from psalter.adapters.persistence import (
    SqliteCatalogImportProgressRepository,
    SqliteDatabase,
    SqliteInstallationSettingsRepository,
    SqliteLearningSessionRepository,
    SqliteMigrator,
    SqlitePassageRepository,
    SqlitePsalmCatalogCommitter,
    SqlitePsalmLearningPlanRepository,
    SqlitePsalmRepository,
    SqliteRecitationCommitter,
    SqliteRecitationRepository,
    SqliteReviewRepository,
    migrations_dir,
)
from psalter.adapters.scripture_catalog_provider import (
    HelloAoScriptureCatalogProvider,
    MockScriptureCatalogProvider,
)
from psalter.adapters.system_clock import SystemClock
from psalter.adapters.transcription import UnsupportedTranscriber, WhisperCppTranscriber
from psalter.application.services.installation import (
    InstallationReadinessService,
    PsalmCatalogInstaller,
)
from psalter.application.services.learning import LearningService
from psalter.application.services.passage import PassageService
from psalter.application.services.progress import ProgressService
from psalter.application.services.psalm import PsalmService
from psalter.application.services.psalm_learning import PsalmLearningService
from psalter.application.services.recitation import (
    RecitationPolicy,
    RecitationService,
    default_recitation_assessor,
)
from psalter.application.services.review import ReviewService
from psalter.application.services.scheduling import InitialReviewSchedulingPolicy
from psalter.application.services.segmentation import WordCountSegmentationPolicy
from psalter.application.services.spoken_recitation import (
    ArtifactRetentionPolicy,
    SpokenRecitationService,
)
from psalter.config import AppConfig, build_config


@dataclass(frozen=True, slots=True)
class Container:
    config: AppConfig
    db: SqliteDatabase
    migrator: SqliteMigrator
    psalm_service: PsalmService
    passage_service: PassageService
    learning_service: LearningService
    psalm_learning_service: PsalmLearningService
    recitation_service: RecitationService
    spoken_recitation_service: SpokenRecitationService
    review_service: ReviewService
    progress_service: ProgressService
    installer: PsalmCatalogInstaller
    installation_readiness: InstallationReadinessService


def build_container(config: AppConfig | None = None) -> Container:
    resolved = config or build_config()
    db = SqliteDatabase(path=resolved.db_path)
    migrator = SqliteMigrator(database=db, migrations_dir=migrations_dir())
    clock = SystemClock()

    passage_repo = SqlitePassageRepository(db)
    psalm_repo = SqlitePsalmRepository(db)
    plan_repo = SqlitePsalmLearningPlanRepository(db)
    learning_repo = SqliteLearningSessionRepository(db)
    recitation_repo = SqliteRecitationRepository(db)
    review_repo = SqliteReviewRepository(db)
    installation_repo = SqliteInstallationSettingsRepository(db)
    import_progress_repo = SqliteCatalogImportProgressRepository(db)
    catalog_committer = SqlitePsalmCatalogCommitter(db)
    recitation_committer = SqliteRecitationCommitter(db)
    segmentation_policy = WordCountSegmentationPolicy()
    scripture_provider = build_scripture_provider(resolved)

    psalm_service = PsalmService(psalms=psalm_repo, segmentation_policy=segmentation_policy)
    passage_service = PassageService(passages=passage_repo, psalms=psalm_repo)
    learning_service = LearningService(passages=passage_repo, sessions=learning_repo, clock=clock)
    recitation_service = RecitationService(
        passages=passage_repo,
        sessions=learning_repo,
        reviews=review_repo,
        committer=recitation_committer,
        assessor=default_recitation_assessor(),
        scheduling_policy=InitialReviewSchedulingPolicy(),
        policy=RecitationPolicy(required_passes_to_learn=2),
        clock=clock,
    )
    recorder = (
        FfmpegAudioRecorder(resolved.recorder)
        if resolved.recorder is not None
        else UnsupportedAudioRecorder()
    )
    transcriber = (
        WhisperCppTranscriber(resolved.whisper_cpp)
        if resolved.whisper_cpp is not None
        else UnsupportedTranscriber()
    )
    retention_policy = (
        ArtifactRetentionPolicy.RETAIN
        if (resolved.whisper_cpp and resolved.whisper_cpp.retain_artifacts)
        or (resolved.recorder and resolved.recorder.retain_artifacts)
        else ArtifactRetentionPolicy.DELETE
    )
    spoken_recitation_service = SpokenRecitationService(
        recorder=recorder,
        transcriber=transcriber,
        recitation_service=recitation_service,
        retention_policy=retention_policy,
    )
    review_service = ReviewService(
        reviews=review_repo,
        clock=clock,
        passages=passage_repo,
        psalms=psalm_repo,
    )
    installer = PsalmCatalogInstaller(
        provider_name=resolved.scripture_provider,
        provider=scripture_provider,
        settings=installation_repo,
        progress=import_progress_repo,
        committer=catalog_committer,
        psalms=psalm_repo,
        passages=passage_repo,
        segmentation_policy=segmentation_policy,
        clock=clock,
    )
    readiness = InstallationReadinessService(settings=installation_repo)
    installed_default = installation_repo.get_settings()
    resolved_default_translation_id = (
        installed_default.default_translation_id
        if installed_default is not None and installed_default.default_translation_id is not None
        else resolved.default_translation_id
    )
    psalm_learning_service = PsalmLearningService(
        psalms=psalm_repo,
        plans=plan_repo,
        passages=passage_repo,
        sessions=learning_repo,
        learning_service=learning_service,
        clock=clock,
        default_translation_id=resolved_default_translation_id,
    )
    progress_service = ProgressService(
        passages=passage_repo,
        sessions=learning_repo,
        attempts=recitation_repo,
        reviews=review_repo,
        clock=clock,
    )

    return Container(
        config=resolved,
        db=db,
        migrator=migrator,
        psalm_service=psalm_service,
        passage_service=passage_service,
        learning_service=learning_service,
        psalm_learning_service=psalm_learning_service,
        recitation_service=recitation_service,
        spoken_recitation_service=spoken_recitation_service,
        review_service=review_service,
        progress_service=progress_service,
        installer=installer,
        installation_readiness=readiness,
    )


def initialize_storage(config: AppConfig | None = None) -> AppConfig:
    container = build_container(config)
    container.migrator.apply_pending()
    return container.config


def build_scripture_provider(
    config: AppConfig,
) -> HelloAoScriptureCatalogProvider | MockScriptureCatalogProvider:
    if config.scripture_provider == "mock":
        return MockScriptureCatalogProvider()
    return HelloAoScriptureCatalogProvider(
        base_url=config.scripture_provider_base_url,
        timeout_seconds=config.scripture_provider_timeout_seconds,
    )
