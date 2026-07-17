from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from psalter.application.dto import AlignmentIssueDTO, RecitationAssessmentDTO, RecitationSubmission
from psalter.application.errors import (
    InvalidLearningTransitionError,
    LearningSessionNotFoundError,
    PassageNotFoundError,
)
from psalter.application.services.assessment import AssessmentResult, TypedTextAssessmentPolicy
from psalter.application.services.normalization import (
    normalize_lines,
    normalize_text,
    normalize_tokens,
)
from psalter.application.services.scheduling import InitialReviewSchedulingPolicy
from psalter.domain.errors import InvalidTransitionError
from psalter.domain.learning import LearningPhase
from psalter.domain.recitation import (
    AlignmentKind,
    RecitationAttempt,
    RecitationResult,
    RecitationSource,
)
from psalter.ports.clock import Clock
from psalter.ports.learning_repository import LearningRepository
from psalter.ports.passage_repository import PassageRepository
from psalter.ports.recitation_committer import RecitationCommitter
from psalter.ports.review_repository import ReviewRepository


class RecitationAssessor(Protocol):
    def assess(
        self,
        expected_tokens: tuple[str, ...],
        expected_lines: tuple[tuple[str, ...], ...],
        submitted_tokens: tuple[str, ...],
    ) -> AssessmentResult: ...


@dataclass(frozen=True, slots=True)
class RecitationPolicy:
    required_passes_to_learn: int = 2


class RecitationService:
    def __init__(
        self,
        passages: PassageRepository,
        sessions: LearningRepository,
        reviews: ReviewRepository,
        committer: RecitationCommitter,
        assessor: RecitationAssessor,
        scheduling_policy: InitialReviewSchedulingPolicy,
        policy: RecitationPolicy,
        clock: Clock,
    ) -> None:
        self._passages = passages
        self._sessions = sessions
        self._reviews = reviews
        self._committer = committer
        self._assessor = assessor
        self._scheduling_policy = scheduling_policy
        self._policy = policy
        self._clock = clock

    def submit_text(self, submission: RecitationSubmission) -> RecitationAssessmentDTO:
        if submission.source not in (RecitationSource.TYPED, RecitationSource.SPEECH_TRANSCRIPT):
            raise InvalidLearningTransitionError(
                f"Unsupported submission source: {submission.source}"
            )

        passage = self._passages.get_by_id(submission.passage_id)
        if passage is None:
            raise PassageNotFoundError(f"Passage not found: {submission.passage_id}")
        session = self._sessions.get_by_passage(submission.passage_id)
        if session is None:
            raise LearningSessionNotFoundError(
                f"Learning session not found for passage: {submission.passage_id}"
            )
        if session.phase is not LearningPhase.READY_FOR_RECITATION:
            raise InvalidLearningTransitionError(
                "Recitation submission is only allowed when session is ready_for_recitation"
            )

        expected_tokens = normalize_tokens(passage.canonical_text)
        expected_lines = normalize_lines(passage.canonical_text)
        normalized_submission = normalize_text(submission.text)
        submitted_tokens = tuple(normalized_submission.split()) if normalized_submission else ()
        assessed = self._assessor.assess(expected_tokens, expected_lines, submitted_tokens)
        now = self._clock.now()

        updated_session = session
        review_state = None
        if assessed.result is RecitationResult.PASS:
            try:
                updated_session = session.record_successful_recitation(
                    required_passes=self._policy.required_passes_to_learn,
                    when=now,
                )
            except InvalidTransitionError as exc:
                raise InvalidLearningTransitionError(str(exc)) from exc
            if updated_session.phase is LearningPhase.LEARNED:
                review_state = self._reviews.get_by_passage(submission.passage_id)
                if review_state is None:
                    review_state = self._scheduling_policy.create_initial_state(
                        passage_id=submission.passage_id,
                        learned_at=now,
                    )
        elif assessed.result is RecitationResult.RETRY:
            try:
                updated_session = session.mark_needs_reinforcement(now)
            except InvalidTransitionError as exc:
                raise InvalidLearningTransitionError(str(exc)) from exc

        attempt = RecitationAttempt(
            id=str(uuid4()),
            passage_id=submission.passage_id,
            learning_session_id=session.id,
            source=submission.source,
            submitted_text=submission.text,
            normalized_text=normalized_submission,
            attempted_at=now,
            result=assessed.result,
            weighted_accuracy=assessed.weighted_accuracy,
            assessment_policy_version=assessed.policy_version,
            omission_count=assessed.omission_count,
            substitution_count=assessed.substitution_count,
            insertion_count=assessed.insertion_count,
            longest_omitted_span=assessed.longest_omitted_span,
            alignment_diagnostics=assessed.alignment,
        )
        self._committer.commit_assessment(
            attempt=attempt, session=updated_session, review_state=review_state
        )

        remaining_successes_required = max(
            0,
            self._policy.required_passes_to_learn - updated_session.successful_blank_recitations,
        )
        issues = tuple(
            AlignmentIssueDTO(
                kind=op.kind,
                expected_token=op.expected_token,
                submitted_token=op.submitted_token,
            )
            for op in assessed.alignment
            if op.kind
            in (AlignmentKind.OMISSION, AlignmentKind.SUBSTITUTION, AlignmentKind.INSERTION)
        )
        return RecitationAssessmentDTO(
            attempt_id=attempt.id,
            passage_id=attempt.passage_id,
            learning_session_id=attempt.learning_session_id,
            source=attempt.source,
            result=attempt.result,
            weighted_accuracy=attempt.weighted_accuracy,
            omission_count=assessed.omission_count,
            substitution_count=assessed.substitution_count,
            insertion_count=assessed.insertion_count,
            longest_omitted_span=assessed.longest_omitted_span,
            policy_version=assessed.policy_version,
            failure_reasons=assessed.failure_reasons,
            omissions=assessed.omissions,
            substitutions=assessed.substitutions,
            insertions=assessed.insertions,
            remaining_successes_required=remaining_successes_required,
            issues=issues,
        )


def default_recitation_assessor() -> RecitationAssessor:
    return TypedTextAssessmentPolicy()
