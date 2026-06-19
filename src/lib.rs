use pyo3::prelude::*;
use regex::Regex;
use std::sync::OnceLock;

// One compiled rule tied to a graph concept name
struct CompiledRule {
    pattern_id: &'static str,
    concept: &'static str,
    category: &'static str,
    action: &'static str,
    regex: Regex,
}

// Rule definitions — concept names must match Neo4j RestrictedConcept nodes
const RULE_SPECS: &[(&str, &str, &str, &str, &str)] = &[
    (
        "finra_guaranteed_return",
        r"(?i)guarantee.*return",
        "Guaranteed Returns",
        "FINRA",
        "APPEND",
    ),
    (
        "finra_promise_money",
        r"(?i)promise.*make\s*money",
        "Guaranteed Returns",
        "FINRA",
        "APPEND",
    ),
    (
        "finra_zero_risk",
        r"(?i)zero\s*risk",
        "Risk-Free Investment",
        "FINRA",
        "APPEND",
    ),
    (
        "finra_100_safe",
        r"(?i)100%\s*safe",
        "Risk-Free Investment",
        "FINRA",
        "APPEND",
    ),
    (
        "healthcare_guaranteed_cure",
        r"(?i)guarantee.*cure",
        "Guaranteed Cure",
        "HEALTHCARE",
        "BLOCK",
    ),
    (
        "healthcare_absolute_cure",
        r"(?i)absolute.*cure",
        "Guaranteed Cure",
        "HEALTHCARE",
        "BLOCK",
    ),
    (
        "healthcare_absolute_healing",
        r"(?i)absolute.*healing",
        "Guaranteed Cure",
        "HEALTHCARE",
        "BLOCK",
    ),
    (
        "healthcare_definitive_diagnosis",
        r"(?i)definitive.*diagnosis",
        "Definitive Diagnosis",
        "HEALTHCARE",
        "REDACT",
    ),
];

fn compiled_rules() -> &'static Vec<CompiledRule> {
    static RULES: OnceLock<Vec<CompiledRule>> = OnceLock::new();
    RULES.get_or_init(|| {
        RULE_SPECS
            .iter()
            .map(|(id, pattern, concept, category, action)| CompiledRule {
                pattern_id: id,
                concept,
                category,
                action,
                regex: Regex::new(pattern).expect("invalid rule regex"),
            })
            .collect()
    })
}

#[pyclass(skip_from_py_object)]
#[derive(Clone)]
struct Violation {
    #[pyo3(get)]
    concept: String,
    #[pyo3(get)]
    category: String,
    #[pyo3(get)]
    action: String,
    #[pyo3(get)]
    pattern_id: String,
}

#[pyfunction]
fn scan_for_violations(llm_output: &str) -> PyResult<Vec<Violation>> {
    let mut seen = Vec::new();
    let mut violations = Vec::new();

    for rule in compiled_rules() {
        if !rule.regex.is_match(llm_output) {
            continue;
        }
        // Deduplicate by concept so each policy fires once
        if seen.contains(&rule.concept) {
            continue;
        }
        seen.push(rule.concept);
        violations.push(Violation {
            concept: rule.concept.to_string(),
            category: rule.category.to_string(),
            action: rule.action.to_string(),
            pattern_id: rule.pattern_id.to_string(),
        });
    }

    Ok(violations)
}

#[pymodule]
fn neuro_symbolic_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Violation>()?;
    m.add_function(wrap_pyfunction!(scan_for_violations, m)?)?;
    Ok(())
}
