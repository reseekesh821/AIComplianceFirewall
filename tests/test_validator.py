import neuro_symbolic_validator
from policy import apply_policy, append_disclaimers


def test_clean_text_has_no_violations():
    text = (
        "Investing involves risk, and past performance is not "
        "indicative of future results."
    )
    violations = neuro_symbolic_validator.scan_for_violations(text)
    assert len(violations) == 0


def test_finra_violation_returns_concept():
    text = "This portfolio offers a guaranteed return with zero risk."
    violations = neuro_symbolic_validator.scan_for_violations(text)
    concepts = {v.concept for v in violations}
    assert "Guaranteed Returns" in concepts
    assert "Risk-Free Investment" in concepts
    assert all(v.category == "FINRA" for v in violations)


def test_healthcare_block_action():
    text = "This treatment is a guaranteed cure for cancer."
    violations = neuro_symbolic_validator.scan_for_violations(text)
    assert any(v.action == "BLOCK" for v in violations)
    result = apply_policy(text, violations)
    assert result.action == "BLOCK"
    assert result.status == "Blocked"


def test_healthcare_redact_action():
    text = "Based on symptoms, the definitive diagnosis is diabetes."
    violations = neuro_symbolic_validator.scan_for_violations(text)
    result = apply_policy(text, violations)
    assert result.action == "REDACT"
    assert "[REDACTED" in result.final_output


def test_append_disclaimers_format():
    output = append_disclaimers(
        "Sample pitch.",
        ["All investments involve risk."],
        ["FINRA"],
    )
    assert "REQUIRED FINRA COMPLIANCE DISCLOSURE" in output
    assert "All investments involve risk." in output


def test_policy_pass_on_clean_text():
    text = "General educational content about markets."
    violations = neuro_symbolic_validator.scan_for_violations(text)
    result = apply_policy(text, violations)
    assert result.action == "PASS"
    assert result.status == "Clean"
