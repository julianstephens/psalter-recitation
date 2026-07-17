from __future__ import annotations

from dataclasses import dataclass

from psalter.application.dto import (
    PassageDetailDTO,
    PsalmDetailDTO,
    PsalmLearningPlanDTO,
    PsalmLearningViewDTO,
    PsalmProgressDTO,
    PsalmVerseDTO,
)
from psalter.application.errors import (
    InvalidLearningTransitionError,
    NoActivePassageError,
    PersistenceConflictError,
    PsalmLearningPlanConflictError,
    PsalmNotFoundError,
    PsalmTranslationAmbiguousError,
    WholePsalmConsolidationUnavailableError,
)
from psalter.application.services.learning import LearningService
from psalter.domain.errors import InvalidTransitionError
from psalter.domain.learning import LearningPhase
from psalter.domain.passage import Passage, PassageKind
from psalter.domain.psalm import Psalm, PsalmCompleteness, PsalmLearningPlan, PsalmLearningStatus
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.psalm_repository import PsalmLearningPlanRepository, PsalmRepository


@dataclass(frozen=True, slots=True)
class PsalmResolution:
    psalm: Psalm
    defaulted_translation: bool = False


class PsalmLearningService:
    def __init__(
        self,
        *,
        psalms: PsalmRepository,
        plans: PsalmLearningPlanRepository,
        passages: PassageRepository,
        sessions: LearningRepository,
        learning_service: LearningService,
        clock: Clock,
        default_translation_id: str | None = None,
    ) -> None:
        self._psalms = psalms
        self._plans = plans
        self._passages = passages
        self._sessions = sessions
        self._learning_service = learning_service
        self._clock = clock
        self._default_translation_id = default_translation_id

    def begin_or_resume(
        self,
        psalm_number: int,
        translation_id: str | None = None,
    ) -> PsalmLearningViewDTO:
        psalm = self._resolve_psalm(psalm_number=psalm_number, translation_id=translation_id)
        plan = self._ensure_plan(psalm)
        active = (
            self._passages.get_by_id(plan.active_passage_id) if plan.active_passage_id else None
        )
        if active is not None:
            self._learning_service.begin_or_resume(active.id)
        return self._build_learning_view(psalm, plan)

    def get_learning_view(
        self,
        psalm_number: int,
        translation_id: str | None = None,
    ) -> PsalmLearningViewDTO:
        psalm = self._resolve_psalm(psalm_number=psalm_number, translation_id=translation_id)
        plan = self._require_plan(psalm.id)
        active = (
            self._passages.get_by_id(plan.active_passage_id) if plan.active_passage_id else None
        )
        if active is not None:
            self._learning_service.begin_or_resume(active.id)
        return self._build_learning_view(psalm, plan)

    def resolve_active_passage(self, psalm_id: str) -> PassageDetailDTO:
        plan = self._require_plan(psalm_id)
        passage = self._require_active_passage(plan)
        return self._learning_service.get_passage(passage.id)

    def advance_after_passage_learned(self, psalm_id: str) -> PsalmLearningViewDTO:
        psalm = self._require_psalm(psalm_id)
        plan = self._require_plan(psalm.id)
        active = self._require_active_passage(plan)
        session = self._sessions.get_by_passage(active.id)
        if session is None or session.phase is not LearningPhase.LEARNED:
            return self._build_learning_view(psalm, plan)

        now = self._clock.now()
        try:
            if active.kind is PassageKind.SECTION:
                next_section = self._next_unlearned_section(psalm.id)
                if next_section is not None:
                    updated = plan.activate_passage(next_section.id, now)
                elif psalm.completeness is PsalmCompleteness.COMPLETE:
                    consolidation = self._passages.get_consolidation_passage(psalm.id)
                    if consolidation is None:
                        raise WholePsalmConsolidationUnavailableError(
                            "Whole-Psalm consolidation is unavailable for "
                            f"Psalm {psalm.psalm_number}."
                        )
                    updated = plan.begin_consolidation(consolidation.id, now)
                else:
                    updated = plan.begin_consolidation(None, now)
            else:
                updated = plan.mark_learned(now)
        except InvalidTransitionError as exc:
            raise InvalidLearningTransitionError(str(exc)) from exc

        self._save_plan(updated, expected_version=plan.version)
        if updated.active_passage_id is not None:
            next_passage = self._passages.get_by_id(updated.active_passage_id)
            if next_passage is not None:
                self._learning_service.begin_or_resume(next_passage.id)
        return self._build_learning_view(psalm, updated)

    def get_progress(
        self,
        psalm_number: int,
        translation_id: str | None = None,
    ) -> PsalmProgressDTO:
        psalm = self._resolve_psalm(psalm_number=psalm_number, translation_id=translation_id)
        return self._build_progress(psalm)

    def list_progress(self) -> list[PsalmProgressDTO]:
        return [self._build_progress(psalm) for psalm in self._psalms.list_all()]

    def _build_progress(self, psalm: Psalm) -> PsalmProgressDTO:
        plan = self._plans.get_by_psalm_id(psalm.id) or self._synthesize_plan(psalm)
        sections = self._section_passages(psalm.id)
        sections_learned = sum(
            1
            for passage in sections
            if (session := self._sessions.get_by_passage(passage.id)) is not None
            and session.phase is LearningPhase.LEARNED
        )
        active = (
            self._passages.get_by_id(plan.active_passage_id) if plan.active_passage_id else None
        )
        current_section_label = (
            _passage_label(active)
            if active is not None and active.kind is PassageKind.SECTION
            else ("complete Psalm" if active is not None else None)
        )
        return PsalmProgressDTO(
            psalm_id=psalm.id,
            translation_id=psalm.translation_id,
            psalm_number=psalm.psalm_number,
            status=plan.status,
            section_count=len(sections),
            sections_learned=sections_learned,
            current_section_label=current_section_label,
            reviews_due=0,
            consolidation_available=psalm.completeness is PsalmCompleteness.COMPLETE,
        )

    def _build_learning_view(self, psalm: Psalm, plan: PsalmLearningPlan) -> PsalmLearningViewDTO:
        active = (
            self._passages.get_by_id(plan.active_passage_id) if plan.active_passage_id else None
        )
        sections = self._section_passages(psalm.id)
        learned_ids = {
            passage.id
            for passage in sections
            if (session := self._sessions.get_by_passage(passage.id)) is not None
            and session.phase is LearningPhase.LEARNED
        }
        return PsalmLearningViewDTO(
            psalm=_to_psalm_detail_dto(psalm),
            plan=PsalmLearningPlanDTO(
                psalm_id=plan.psalm_id,
                status=plan.status,
                active_passage_id=plan.active_passage_id,
                started_at=plan.started_at,
                updated_at=plan.updated_at,
                completed_at=plan.completed_at,
            ),
            active_passage=_to_passage_detail_dto(active) if active is not None else None,
            section_index=_section_index(active, sections),
            section_count=len(sections),
            sections_learned=len(learned_ids),
            consolidation_available=psalm.completeness is PsalmCompleteness.COMPLETE,
        )

    def _ensure_plan(self, psalm: Psalm) -> PsalmLearningPlan:
        existing = self._plans.get_by_psalm_id(psalm.id)
        if existing is not None:
            return existing
        plan = self._synthesize_plan(psalm)
        self._save_plan(plan)
        return plan

    def _synthesize_plan(self, psalm: Psalm) -> PsalmLearningPlan:
        now = self._clock.now()
        sections = self._section_passages(psalm.id)
        first_unlearned = self._first_unlearned_section(psalm.id)
        if first_unlearned is not None:
            first_started_at = min(
                (
                    session.started_at
                    for section in sections
                    if (session := self._sessions.get_by_passage(section.id)) is not None
                ),
                default=now,
            )
            return PsalmLearningPlan(
                psalm_id=psalm.id,
                status=PsalmLearningStatus.LEARNING_SECTIONS,
                active_passage_id=first_unlearned.id,
                started_at=first_started_at,
                updated_at=now,
                completed_at=None,
            )

        consolidation = self._passages.get_consolidation_passage(psalm.id)
        if consolidation is not None:
            consolidation_session = self._sessions.get_by_passage(consolidation.id)
            if (
                consolidation_session is not None
                and consolidation_session.phase is LearningPhase.LEARNED
            ):
                completed_at = (
                    consolidation_session.completed_at or consolidation_session.updated_at
                )
                return PsalmLearningPlan(
                    psalm_id=psalm.id,
                    status=PsalmLearningStatus.LEARNED,
                    active_passage_id=None,
                    started_at=consolidation_session.started_at,
                    updated_at=consolidation_session.updated_at,
                    completed_at=completed_at,
                )
            return PsalmLearningPlan(
                psalm_id=psalm.id,
                status=PsalmLearningStatus.CONSOLIDATING,
                active_passage_id=consolidation.id,
                started_at=now,
                updated_at=now,
                completed_at=None,
            )

        return PsalmLearningPlan(
            psalm_id=psalm.id,
            status=PsalmLearningStatus.CONSOLIDATING,
            active_passage_id=None,
            started_at=now,
            updated_at=now,
            completed_at=None,
        )

    def _resolve_psalm(self, *, psalm_number: int, translation_id: str | None) -> Psalm:
        requested_translation = translation_id.strip() if translation_id else None
        if requested_translation:
            psalm = self._psalms.get_by_translation_and_number(requested_translation, psalm_number)
            if psalm is None:
                raise PsalmNotFoundError(
                    f"Psalm {psalm_number} was not found for translation {requested_translation}."
                )
            return psalm
        if self._default_translation_id:
            psalm = self._psalms.get_by_translation_and_number(
                self._default_translation_id,
                psalm_number,
            )
            if psalm is not None:
                return psalm
        matches = self._psalms.list_by_number(psalm_number)
        if not matches:
            raise PsalmNotFoundError(f"Psalm {psalm_number} was not found.")
        if len(matches) == 1:
            return matches[0]
        available = ", ".join(sorted(psalm.translation_id for psalm in matches))
        raise PsalmTranslationAmbiguousError(
            f"Psalm {psalm_number} is available in multiple translations: {available}. "
            "Pass --translation-id or configure PSALTER_DEFAULT_TRANSLATION."
        )

    def _require_psalm(self, psalm_id: str) -> Psalm:
        psalm = self._psalms.get_by_id(psalm_id)
        if psalm is None:
            raise PsalmNotFoundError(f"Psalm not found: {psalm_id}")
        return psalm

    def _require_plan(self, psalm_id: str) -> PsalmLearningPlan:
        plan = self._plans.get_by_psalm_id(psalm_id)
        if plan is None:
            psalm = self._require_psalm(psalm_id)
            plan = self._synthesize_plan(psalm)
            self._save_plan(plan)
        return plan

    def _require_active_passage(self, plan: PsalmLearningPlan) -> Passage:
        if plan.active_passage_id is None:
            raise NoActivePassageError(f"No active passage for Psalm plan {plan.psalm_id}")
        passage = self._passages.get_by_id(plan.active_passage_id)
        if passage is None:
            raise NoActivePassageError(f"Active passage not found: {plan.active_passage_id}")
        return passage

    def _save_plan(self, plan: PsalmLearningPlan, expected_version: int | None = None) -> None:
        try:
            self._plans.upsert(plan, expected_version=expected_version)
        except PersistenceConflictError as exc:
            raise PsalmLearningPlanConflictError(
                f"Psalm learning plan changed during update for {plan.psalm_id}; retry."
            ) from exc

    def _section_passages(self, psalm_id: str) -> list[Passage]:
        return self._passages.list_by_psalm(psalm_id, kind=PassageKind.SECTION)

    def _first_unlearned_section(self, psalm_id: str) -> Passage | None:
        for passage in self._section_passages(psalm_id):
            session = self._sessions.get_by_passage(passage.id)
            if session is None or session.phase is not LearningPhase.LEARNED:
                return passage
        return None

    def _next_unlearned_section(self, psalm_id: str) -> Passage | None:
        return self._first_unlearned_section(psalm_id)


def _section_index(active: Passage | None, sections: list[Passage]) -> int | None:
    if active is None or active.kind is not PassageKind.SECTION:
        return None
    for index, section in enumerate(sections, start=1):
        if section.id == active.id:
            return index
    return None


def _passage_label(passage: Passage) -> str:
    if passage.start_verse == passage.end_verse:
        return f"verse {passage.start_verse}"
    return f"verses {passage.start_verse}-{passage.end_verse}"


def _to_psalm_detail_dto(psalm: Psalm) -> PsalmDetailDTO:
    return PsalmDetailDTO(
        id=psalm.id,
        translation_id=psalm.translation_id,
        psalm_number=psalm.psalm_number,
        canonical_text=psalm.canonical_text,
        verse_count=psalm.verse_count,
        completeness=psalm.completeness,
        verses=tuple(
            PsalmVerseDTO(verse_number=verse.verse_number, canonical_text=verse.canonical_text)
            for verse in psalm.verses
        ),
    )


def _to_passage_detail_dto(passage: Passage) -> PassageDetailDTO:
    return PassageDetailDTO(
        id=passage.id,
        psalm_id=passage.psalm_id,
        translation_id=passage.translation_id,
        psalm_number=passage.psalm_number,
        start_verse=passage.start_verse,
        end_verse=passage.end_verse,
        canonical_text=passage.canonical_text,
        sequence_number=passage.sequence_number,
        kind=passage.kind,
        segmentation_policy_version=passage.segmentation_policy_version,
    )
