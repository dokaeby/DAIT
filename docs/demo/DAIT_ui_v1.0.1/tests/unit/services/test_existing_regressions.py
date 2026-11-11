"""Run existing pure tests inside the new isolation guard; HTTP tests stay separate."""

import importlib

import pytest

CASES = [
    ("test_ai_summary", "SummaryTests", "test_missing_and_generated"),
    ("test_ai_summary", "SummaryTests", "test_states_and_latest_failure"),
    ("test_domestic", "DomesticTests", "test_selection_without_writes"),
    ("test_domestic", "DomesticTests", "test_reuse_and_force"),
    ("test_domestic", "DomesticTests", "test_latest_error_stale_invalid"),
    ("test_foreign", "ForeignTests", "test_missing_and_generated"),
    ("test_foreign", "ForeignTests", "test_insufficient_latest_error_and_stale"),
    ("test_foreign", "ForeignTests", "test_invalid_language_and_duplicate_lines"),
    ("test_compare", "CompareTests", "test_vectors_and_cosine"),
    ("test_compare", "CompareTests", "test_hybrid_ranking"),
    ("test_compare", "CompareTests", "test_keyword_and_cache_invalidation"),
    ("test_compare", "CompareTests", "test_embedding_response_contract"),
    ("test_compare", "CompareTests", "test_e5_input_prefixes"),
    ("test_compare", "CompareTests", "test_cpu_model_load_and_version_identity"),
    (
        "test_compare",
        "CompareTests",
        "test_display_scores_include_keyword_below_threshold",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_reconcile_reuses_and_deduplicates",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_success_is_saved_and_not_generated_again",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_failure_stops_after_three_attempts_and_preserves_history",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_result_storage_failure_is_not_success",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_provider_result_is_saved_by_worker",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_provider_failure_is_recorded_and_retried",
    ),
    (
        "test_summary_service",
        "SummaryWorkerTests",
        "test_card_shows_escaped_saved_summary",
    ),
    ("test_search", "SearchTests", "test_search_before_limit_and_scope"),
    ("test_search", "SearchTests", "test_literal_characters_and_normalization"),
    ("test_search", "SearchTests", "test_foreign_title_and_escaping"),
]


@pytest.mark.extension
@pytest.mark.parametrize("module_name,class_name,method", CASES, ids=[case[2] for case in CASES])
def test_existing_pure_regression(module_name, class_name, method):
    module = importlib.import_module("tests." + module_name)
    case = getattr(module, class_name)(methodName=method)
    case.setUp()
    try:
        getattr(case, method)()
    finally:
        case.tearDown()
