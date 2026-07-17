from __future__ import annotations

from dataclasses import dataclass

from psalter.domain.recitation import AlignmentKind, AlignmentOperation


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    operations: tuple[AlignmentOperation, ...]
    omission_count: int
    substitution_count: int
    insertion_count: int
    longest_omitted_span: int


def align_tokens(expected: tuple[str, ...], submitted: tuple[str, ...]) -> AlignmentResult:
    n = len(expected)
    m = len(submitted)
    costs: list[list[int]] = [[0] * (m + 1) for _ in range(n + 1)]
    pointers: list[list[AlignmentKind | None]] = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        costs[i][0] = i
        pointers[i][0] = AlignmentKind.OMISSION
    for j in range(1, m + 1):
        costs[0][j] = j
        pointers[0][j] = AlignmentKind.INSERTION

    tie_breaker = {
        AlignmentKind.MATCH: 0,
        AlignmentKind.SUBSTITUTION: 1,
        AlignmentKind.OMISSION: 2,
        AlignmentKind.INSERTION: 3,
    }

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            exp = expected[i - 1]
            sub = submitted[j - 1]
            diagonal_kind = AlignmentKind.MATCH if exp == sub else AlignmentKind.SUBSTITUTION
            diagonal_cost = costs[i - 1][j - 1] + (0 if diagonal_kind is AlignmentKind.MATCH else 1)
            omission_cost = costs[i - 1][j] + 1
            insertion_cost = costs[i][j - 1] + 1

            candidates = (
                (diagonal_cost, diagonal_kind),
                (omission_cost, AlignmentKind.OMISSION),
                (insertion_cost, AlignmentKind.INSERTION),
            )
            best_cost, best_kind = min(candidates, key=lambda item: (item[0], tie_breaker[item[1]]))
            costs[i][j] = best_cost
            pointers[i][j] = best_kind

    i = n
    j = m
    operations: list[AlignmentOperation] = []
    omission_count = 0
    substitution_count = 0
    insertion_count = 0
    longest_omitted_span = 0
    current_omitted_span = 0

    while i > 0 or j > 0:
        kind = pointers[i][j]
        if kind is AlignmentKind.MATCH or kind is AlignmentKind.SUBSTITUTION:
            expected_token = expected[i - 1]
            submitted_token = submitted[j - 1]
            operations.append(
                AlignmentOperation(
                    kind=kind,
                    expected_token=expected_token,
                    submitted_token=submitted_token,
                    expected_index=i - 1,
                    submitted_index=j - 1,
                )
            )
            if kind is AlignmentKind.SUBSTITUTION:
                substitution_count += 1
            current_omitted_span = 0
            i -= 1
            j -= 1
            continue
        if kind is AlignmentKind.OMISSION:
            operations.append(
                AlignmentOperation(
                    kind=AlignmentKind.OMISSION,
                    expected_token=expected[i - 1],
                    submitted_token=None,
                    expected_index=i - 1,
                    submitted_index=None,
                )
            )
            omission_count += 1
            current_omitted_span += 1
            longest_omitted_span = max(longest_omitted_span, current_omitted_span)
            i -= 1
            continue
        if kind is AlignmentKind.INSERTION:
            operations.append(
                AlignmentOperation(
                    kind=AlignmentKind.INSERTION,
                    expected_token=None,
                    submitted_token=submitted[j - 1],
                    expected_index=None,
                    submitted_index=j - 1,
                )
            )
            insertion_count += 1
            current_omitted_span = 0
            j -= 1
            continue
        raise RuntimeError("Alignment pointer missing")

    operations.reverse()
    return AlignmentResult(
        operations=tuple(operations),
        omission_count=omission_count,
        substitution_count=substitution_count,
        insertion_count=insertion_count,
        longest_omitted_span=longest_omitted_span,
    )
