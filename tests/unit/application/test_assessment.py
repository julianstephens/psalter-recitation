from psalter.application.services.assessment import TypedTextAssessmentPolicy
from psalter.application.services.normalization import normalize_lines, normalize_tokens
from psalter.domain.recitation import RecitationResult


def test_assessment_passes_exact_recall() -> None:
    text = "The LORD is my shepherd"
    policy = TypedTextAssessmentPolicy()
    result = policy.assess(
        expected_tokens=normalize_tokens(text),
        expected_lines=normalize_lines(text),
        submitted_tokens=normalize_tokens("the lord is my shepherd"),
    )
    assert result.result is RecitationResult.PASS
    assert result.policy_version == "typed-v1"


def test_assessment_handles_blank_submission_as_retry() -> None:
    text = "The LORD is my shepherd"
    policy = TypedTextAssessmentPolicy()
    result = policy.assess(
        expected_tokens=normalize_tokens(text),
        expected_lines=normalize_lines(text),
        submitted_tokens=(),
    )
    assert result.result is RecitationResult.RETRY


def test_assessment_rejects_substantive_substitutions() -> None:
    text = "he leadeth me beside still waters"
    policy = TypedTextAssessmentPolicy()
    result = policy.assess(
        expected_tokens=normalize_tokens(text),
        expected_lines=normalize_lines(text),
        submitted_tokens=normalize_tokens("he leads me beside still waters"),
    )
    assert result.result is RecitationResult.RETRY
    assert result.substitution_count >= 1
