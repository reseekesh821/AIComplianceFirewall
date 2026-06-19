import uuid
from pathlib import Path

from pydantic import BaseModel

from config import Settings
from llm import get_llm
from policy import PolicyResult, append_disclaimers, evaluate_scan
from scanner import get_scanner, scan_text


class GuardResponse(BaseModel):
    request_id: str
    status: str
    action: str
    concepts: list[str]
    categories: list[str]
    prompt_concepts: list[str] = []
    output_concepts: list[str] = []
    prompt_flagged: bool = False
    final_output: str
    policy_version: str = ""
    raw_llm_output: str = ""


def scan_pair(settings: Settings, prompt: str, llm_output: str):
    rules_path = Path(settings.rules_file)
    prompt_v = scan_text(prompt, rules_path, settings)
    output_v = scan_text(llm_output, rules_path, settings)
    return prompt_v, output_v


def run_guard(
    settings: Settings,
    prompt: str,
    llm_output: str | None,
    neo4j_driver,
) -> GuardResponse:
    request_id = str(uuid.uuid4())
    rules_path = Path(settings.rules_file)
    policy_version = get_scanner(rules_path).pack.version

    if llm_output is None:
        try:
            llm_output = get_llm(settings).generate(prompt)
        except Exception:
            return GuardResponse(
                request_id=request_id,
                status="Error",
                action="ERROR",
                concepts=[],
                categories=[],
                prompt_concepts=[],
                output_concepts=[],
                prompt_flagged=False,
                final_output="Failed to connect to LLM provider.",
                policy_version=policy_version,
                raw_llm_output="",
            )

    prompt_v, output_v = scan_pair(settings, prompt, llm_output)
    result: PolicyResult = evaluate_scan(prompt, llm_output, prompt_v, output_v)

    final_output = result.final_output
    if result.action == "APPEND" and neo4j_driver is not None:
        disclaimers = _get_disclaimers(neo4j_driver, result.output_concepts or result.concepts)
        final_output = append_disclaimers(final_output, disclaimers, result.categories)

    return GuardResponse(
        request_id=request_id,
        status=result.status,
        action=result.action,
        concepts=result.concepts,
        categories=result.categories,
        prompt_concepts=result.prompt_concepts,
        output_concepts=result.output_concepts,
        prompt_flagged=result.prompt_flagged,
        final_output=final_output,
        policy_version=policy_version,
        raw_llm_output=llm_output,
    )


def _get_disclaimers(driver, concepts: list[str]) -> list[str]:
    if not concepts:
        return []
    disclaimers: list[str] = []
    query = """
    MATCH (c:RestrictedConcept {name: $concept})-[:REQUIRES_DISCLAIMER]->(d:Disclaimer)
    RETURN DISTINCT d.text AS disclaimer
    """
    with driver.session() as session:
        for concept in concepts:
            result = session.run(query, concept=concept)
            for record in result:
                disclaimers.append(record["disclaimer"])
    return list(dict.fromkeys(disclaimers))
