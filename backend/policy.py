import re
from dataclasses import dataclass, field


REDACT_PATTERNS = [
    re.compile(r"(?i)definitive\s+diagnosis"),
]

BLOCK_MESSAGE = (
    "This response was blocked because it contained restricted medical claims "
    "that cannot be shown without clinical review."
)

REDACT_REPLACEMENT = "[REDACTED: restricted medical claim removed]"

PROMPT_NOTES = {
    "PROMPT_FLAG": (
        "\n\n--- COMPLIANCE REVIEW NOTE (MARKETING) ---\n"
        "The prompt matched financial marketing rules (e.g. guaranteed returns). "
        "The model output was safe, but the request should be reviewed."
    ),
    "PROMPT_REDACT": (
        "\n\n--- COMPLIANCE REVIEW NOTE (CLINICAL) ---\n"
        "The prompt requested restricted diagnostic language. "
        "The model output was safe, but this clinical request must be reviewed."
    ),
    "PROMPT_BLOCK": (
        "\n\n--- COMPLIANCE REVIEW NOTE (HIGH RISK) ---\n"
        "The prompt matched high-risk medical claim rules (e.g. guaranteed cure). "
        "The model output was safe, but this request requires compliance review."
    ),
}

PROMPT_STATUS = {
    "PROMPT_FLAG": "Marketing Prompt Flagged",
    "PROMPT_REDACT": "Clinical Prompt Flagged",
    "PROMPT_BLOCK": "High-Risk Prompt Flagged",
}


@dataclass
class PolicyResult:
    status: str
    action: str
    final_output: str
    concepts: list[str]
    categories: list[str]
    prompt_concepts: list[str] = field(default_factory=list)
    output_concepts: list[str] = field(default_factory=list)
    prompt_flagged: bool = False


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _concepts(violations) -> list[str]:
    return _unique([v.concept for v in violations])


def _categories(violations) -> list[str]:
    return _unique([v.category for v in violations])


def _strictest_prompt_action(violations) -> str:
    """Map prompt-only violations to a review tier: BLOCK > REDACT > APPEND."""
    actions = {v.action for v in violations}
    if "BLOCK" in actions:
        return "PROMPT_BLOCK"
    if "REDACT" in actions:
        return "PROMPT_REDACT"
    return "PROMPT_FLAG"


def _redact_text(text: str) -> str:
    redacted = text
    for pattern in REDACT_PATTERNS:
        redacted = pattern.sub(REDACT_REPLACEMENT, redacted)
    return redacted


def apply_policy(llm_output: str, violations) -> PolicyResult:
    """Apply enforcement to output violations only: BLOCK > REDACT > APPEND > PASS."""
    if not violations:
        return PolicyResult(
            status="Clean",
            action="PASS",
            final_output=llm_output,
            concepts=[],
            categories=[],
        )

    concepts = _concepts(violations)
    categories = _categories(violations)
    actions = {v.action for v in violations}

    if "BLOCK" in actions:
        return PolicyResult(
            status="Blocked",
            action="BLOCK",
            final_output=BLOCK_MESSAGE,
            concepts=concepts,
            categories=categories,
            output_concepts=concepts,
        )

    if "REDACT" in actions:
        return PolicyResult(
            status="Redacted",
            action="REDACT",
            final_output=_redact_text(llm_output),
            concepts=concepts,
            categories=categories,
            output_concepts=concepts,
        )

    return PolicyResult(
        status="Violation Found",
        action="APPEND",
        final_output=llm_output,
        concepts=concepts,
        categories=categories,
        output_concepts=concepts,
    )


def _prompt_only_result(llm_output: str, prompt_violations) -> PolicyResult:
    action = _strictest_prompt_action(prompt_violations)
    return PolicyResult(
        status=PROMPT_STATUS[action],
        action=action,
        final_output=llm_output + PROMPT_NOTES[action],
        concepts=_concepts(prompt_violations),
        categories=_categories(prompt_violations),
        prompt_concepts=_concepts(prompt_violations),
        output_concepts=[],
        prompt_flagged=True,
    )


def evaluate_scan(prompt: str, llm_output: str, prompt_violations, output_violations) -> PolicyResult:
    """Scan prompt and output; enforce on output, tier prompt-only matches by severity."""
    prompt_concepts = _concepts(prompt_violations)
    prompt_categories = _categories(prompt_violations)
    output_result = apply_policy(llm_output, output_violations)

    if output_result.action != "PASS":
        return PolicyResult(
            status=output_result.status,
            action=output_result.action,
            final_output=output_result.final_output,
            concepts=_unique(prompt_concepts + output_result.concepts),
            categories=_unique(prompt_categories + output_result.categories),
            prompt_concepts=prompt_concepts,
            output_concepts=output_result.output_concepts or _concepts(output_violations),
            prompt_flagged=bool(prompt_violations),
        )

    if prompt_violations:
        return _prompt_only_result(llm_output, prompt_violations)

    return PolicyResult(
        status="Clean",
        action="PASS",
        final_output=llm_output,
        concepts=[],
        categories=[],
        prompt_concepts=[],
        output_concepts=[],
        prompt_flagged=False,
    )


def append_disclaimers(base_output: str, disclaimers: list[str], categories: list[str]) -> str:
    if not disclaimers:
        return base_output
    label = ", ".join(categories)
    lines = "\n".join(f"- {text}" for text in disclaimers)
    return f"{base_output}\n\n--- REQUIRED {label} COMPLIANCE DISCLOSURE ---\n{lines}"
