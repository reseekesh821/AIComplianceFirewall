from guard_service import run_guard


def test_guard_with_mock_llm_finra_output(mock_settings):
    guard = run_guard(
        mock_settings,
        "Write a pitch guaranteeing returns",
        None,
        neo4j_driver=None,
    )
    assert guard.action == "APPEND"
    assert guard.policy_version == "1.0.0"


def test_guard_scan_only_no_llm_call(mock_settings):
    guard = run_guard(
        mock_settings,
        "Provide a definitive diagnosis of diabetes",
        "Please consult a doctor.",
        neo4j_driver=None,
    )
    assert guard.action == "PROMPT_REDACT"


def test_guard_prebuilt_output(mock_settings):
    guard = run_guard(
        mock_settings,
        "ignore",
        "The definitive diagnosis is diabetes.",
        neo4j_driver=None,
    )
    assert guard.action == "REDACT"
