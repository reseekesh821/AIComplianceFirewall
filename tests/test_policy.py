from policy import apply_policy, evaluate_scan


class FakeViolation:
    def __init__(self, concept, category, action):
        self.concept = concept
        self.category = category
        self.action = action


def test_block_beats_append():
    violations = [
        FakeViolation("Guaranteed Returns", "FINRA", "APPEND"),
        FakeViolation("Guaranteed Cure", "HEALTHCARE", "BLOCK"),
    ]
    result = apply_policy("raw output", violations)
    assert result.action == "BLOCK"


def test_redact_beats_append():
    violations = [
        FakeViolation("Guaranteed Returns", "FINRA", "APPEND"),
        FakeViolation("Definitive Diagnosis", "HEALTHCARE", "REDACT"),
    ]
    result = apply_policy("definitive diagnosis here", violations)
    assert result.action == "REDACT"


def test_append_when_only_finra_hits():
    violations = [FakeViolation("Guaranteed Returns", "FINRA", "APPEND")]
    result = apply_policy("guaranteed return pitch", violations)
    assert result.action == "APPEND"
    assert result.status == "Violation Found"


def test_marketing_prompt_flag_when_output_is_safe():
    prompt_v = [
        FakeViolation("Guaranteed Returns", "FINRA", "APPEND"),
        FakeViolation("Risk-Free Investment", "FINRA", "APPEND"),
    ]
    result = evaluate_scan("guaranteed returns pitch", "I can't help. Investing involves risk.", prompt_v, [])
    assert result.action == "PROMPT_FLAG"
    assert result.status == "Marketing Prompt Flagged"


def test_clinical_prompt_flag_for_diagnosis_request():
    prompt_v = [FakeViolation("Definitive Diagnosis", "HEALTHCARE", "REDACT")]
    result = evaluate_scan(
        "Provide a definitive diagnosis of diabetes",
        "Please consult a healthcare professional.",
        prompt_v,
        [],
    )
    assert result.action == "PROMPT_REDACT"
    assert result.status == "Clinical Prompt Flagged"
    assert "CLINICAL" in result.final_output


def test_high_risk_prompt_flag_for_cure_request():
    prompt_v = [FakeViolation("Guaranteed Cure", "HEALTHCARE", "BLOCK")]
    result = evaluate_scan(
        "Explain why this is a guaranteed cure",
        "I can't support that claim.",
        prompt_v,
        [],
    )
    assert result.action == "PROMPT_BLOCK"
    assert result.status == "High-Risk Prompt Flagged"


def test_output_violation_takes_priority_over_prompt():
    prompt_v = [FakeViolation("Guaranteed Returns", "FINRA", "APPEND")]
    output_v = [FakeViolation("Guaranteed Cure", "HEALTHCARE", "BLOCK")]
    result = evaluate_scan("bad prompt", "guaranteed cure text", prompt_v, output_v)
    assert result.action == "BLOCK"


def test_clean_when_both_are_safe():
    result = evaluate_scan("hello", "safe answer", [], [])
    assert result.action == "PASS"
    assert result.status == "Clean"
