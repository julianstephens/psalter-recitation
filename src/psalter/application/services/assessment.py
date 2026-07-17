from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from psalter.application.services.alignment import AlignmentResult, align_tokens
from psalter.domain.recitation import AlignmentKind, AlignmentOperation, RecitationResult


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    result: RecitationResult
    weighted_accuracy: float
    omission_count: int
    substitution_count: int
    insertion_count: int
    longest_omitted_span: int
    alignment: tuple[AlignmentOperation, ...]
    policy_version: str
    failure_reasons: tuple[str, ...]
    omissions: tuple[str, ...]
    substitutions: tuple[tuple[str, str], ...]
    insertions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TypedTextAssessmentPolicy:
    version: str = "typed-v1"
    omission_weight: float = 1.5
    substitution_weight: float = 1.25
    insertion_weight: float = 0.25
    min_weighted_accuracy: float = 0.95
    max_consecutive_omissions: int = 2

    def assess(
        self,
        expected_tokens: tuple[str, ...],
        expected_lines: tuple[tuple[str, ...], ...],
        submitted_tokens: tuple[str, ...],
    ) -> AssessmentResult:
        if not submitted_tokens:
            return AssessmentResult(
                result=RecitationResult.RETRY,
                weighted_accuracy=0.0,
                omission_count=len(expected_tokens),
                substitution_count=0,
                insertion_count=0,
                longest_omitted_span=len(expected_tokens),
                alignment=tuple(
                    AlignmentOperation(
                        kind=AlignmentKind.OMISSION,
                        expected_token=token,
                        submitted_token=None,
                        expected_index=index,
                        submitted_index=None,
                    )
                    for index, token in enumerate(expected_tokens)
                ),
                policy_version=self.version,
                failure_reasons=("submission_blank",),
                omissions=(" ".join(expected_tokens),) if expected_tokens else (),
                substitutions=(),
                insertions=(),
            )

        aligned: AlignmentResult = align_tokens(expected_tokens, submitted_tokens)
        expected_count = max(1, len(expected_tokens))
        weighted_error = (
            aligned.omission_count * self.omission_weight
            + aligned.substitution_count * self.substitution_weight
            + aligned.insertion_count * self.insertion_weight
        )
        weighted_accuracy = max(0.0, 1.0 - (weighted_error / expected_count))
        substitution_limit = max(1, ceil(len(expected_tokens) / 40))

        failure_reasons: list[str] = []
        if weighted_accuracy < self.min_weighted_accuracy:
            failure_reasons.append("weighted_accuracy_below_threshold")
        if aligned.longest_omitted_span > self.max_consecutive_omissions:
            failure_reasons.append("consecutive_omission_limit_exceeded")
        if aligned.substitution_count > substitution_limit:
            failure_reasons.append("substitution_limit_exceeded")
        if len([line for line in expected_lines if line]) > 1 and _has_fully_omitted_nonblank_line(
            expected_lines, aligned.operations
        ):
            failure_reasons.append("omitted_nonblank_canonical_line")

        result = RecitationResult.PASS if not failure_reasons else RecitationResult.RETRY
        omissions, substitutions, insertions = _collect_issues(aligned.operations)
        return AssessmentResult(
            result=result,
            weighted_accuracy=weighted_accuracy,
            omission_count=aligned.omission_count,
            substitution_count=aligned.substitution_count,
            insertion_count=aligned.insertion_count,
            longest_omitted_span=aligned.longest_omitted_span,
            alignment=aligned.operations,
            policy_version=self.version,
            failure_reasons=tuple(failure_reasons),
            omissions=omissions,
            substitutions=substitutions,
            insertions=insertions,
        )


def _collect_issues(
    operations: tuple[AlignmentOperation, ...],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...]]:
    omissions: list[str] = []
    substitutions: list[tuple[str, str]] = []
    insertions: list[str] = []

    current_omission: list[str] = []
    for operation in operations:
        if operation.kind is AlignmentKind.OMISSION and operation.expected_token is not None:
            current_omission.append(operation.expected_token)
            continue
        if current_omission:
            omissions.append(" ".join(current_omission))
            current_omission = []
        if (
            operation.kind is AlignmentKind.SUBSTITUTION
            and operation.expected_token is not None
            and operation.submitted_token is not None
        ):
            substitutions.append((operation.expected_token, operation.submitted_token))
        if operation.kind is AlignmentKind.INSERTION and operation.submitted_token is not None:
            insertions.append(operation.submitted_token)
    if current_omission:
        omissions.append(" ".join(current_omission))

    return tuple(omissions), tuple(substitutions), tuple(insertions)


def _has_fully_omitted_nonblank_line(
    expected_lines: tuple[tuple[str, ...], ...], operations: tuple[AlignmentOperation, ...]
) -> bool:
    omitted_indices = {
        operation.expected_index
        for operation in operations
        if operation.kind is AlignmentKind.OMISSION and operation.expected_index is not None
    }

    offset = 0
    for line in expected_lines:
        if not line:
            continue
        line_indices = range(offset, offset + len(line))
        if all(index in omitted_indices for index in line_indices):
            return True
        offset += len(line)
    return False
