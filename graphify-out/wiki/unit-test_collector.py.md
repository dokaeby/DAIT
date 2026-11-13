# unit/test_collector.py

> 47 nodes

## Key Concepts

- **unit/test_collector.py** (42 connections) — `tests/backend/tests/unit/test_collector.py`
- **RSSCollector** (31 connections) — `src/backend/app/collectors/rss_collector.py`
- **CollectionError** (22 connections) — `src/backend/app/collectors/rss_collector.py`
- **source()** (20 connections) — `tests/backend/tests/unit/test_collector.py`
- **collect()** (16 connections) — `tests/backend/tests/unit/test_collector.py`
- **feed()** (12 connections) — `tests/backend/tests/unit/test_collector.py`
- **handler()** (10 connections) — `tests/backend/tests/unit/test_collector.py`
- **public_dns()** (9 connections) — `tests/backend/tests/unit/test_collector.py`
- **item()** (8 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_redirect_destination_is_checked()** (8 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_robots_errors_fail_closed()** (8 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_transport_error_is_sanitized()** (8 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_compressed_response_is_rejected()** (7 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_dns_rebinding_is_checked_for_every_request()** (7 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_dns_ssrf_is_rejected_before_connection()** (7 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_feed_query_token_is_not_logged()** (7 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_redirect_limit_and_http_failure()** (7 connections) — `tests/backend/tests/unit/test_collector.py`
- **Body** (6 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_successful_relative_redirect()** (6 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_invalid_article_urls_are_rejected()** (5 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_models_are_frozen_and_reject_extra_fields()** (5 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_naive_date_is_rejected_and_optional_body_is_required()** (5 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_sensitive_values_are_not_logged()** (5 connections) — `tests/backend/tests/unit/test_collector.py`
- **test_timeout_is_bounded()** (5 connections) — `tests/backend/tests/unit/test_collector.py`
- **parametrize** (5 connections)
- *... and 22 more nodes in this community*

## Relationships

- [CollectorSource](CollectorSource.md) (19 shared connections)
- [response](response.md) (9 shared connections)
- [ai_processor.py](ai_processor.py.md) (7 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (5 shared connections)
- [CollectionResult](CollectionResult.md) (4 shared connections)
- [5.1 GET `/v1/news/{news_id}`](5.1_GET_`-v1-news-{news_id}`.md) (4 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (3 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (2 shared connections)
- [06_API_설계서_v1.0.3.md](06_API_설계서_v1.0.3.md.md) (2 shared connections)
- [DAIT_ui_v1.0.1/src/backend/src/dait/api/v1/news_routes.py](DAIT_ui_v1.0.1-src-backend-src-dait-api-v1-news_routes.py.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `src/backend/app/collectors/rss_collector.py`
- `tests/backend/tests/unit/test_collector.py`

## Audit Trail

- EXTRACTED: 137 (72%)
- INFERRED: 52 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*