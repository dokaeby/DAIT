# test_app_news_api.py

> 42 nodes

## Key Concepts

- **test_app_news_api.py** (47 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **v1/news.py** (32 connections) — `src/backend/app/api/v1/news.py`
- **NewsListResponse** (23 connections) — `src/backend/app/schemas/news.py`
- **FakeNewsService** (19 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **ApiErrorResponse** (13 connections) — `src/backend/app/schemas/news.py`
- **AsyncClient** (12 connections)
- **asyncio** (12 connections)
- **create_app()** (8 connections) — `src/backend/app/api/v1/news.py`
- **test_openapi_uses_contract_response_models()** (8 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_service_failure_does_not_leak_details()** (7 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_invalid_query_returns_generalized_422_without_service_call()** (6 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_list_defaults_and_exact_response_contract()** (6 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_response_model_rejects_bypassed_invalid_output()** (6 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **client()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **no_real_network()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_missing_opaque_id_returns_404_with_request_id()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_opaque_detail_id_contract_and_nested_fields()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_parameters_are_validated_and_forwarded()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_invalid_cursor_is_sanitized_422()** (4 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_request_ids_are_unique_per_request()** (4 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_valid_page_sizes()** (4 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **parametrize** (4 connections)
- **_ErrorDocumentation** (3 connections) — `src/backend/app/api/v1/news.py`
- **fake_service()** (3 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **fixture** (3 connections)
- *... and 17 more nodes in this community*

## Relationships

- [news_service.py](news_service.py.md) (39 shared connections)
- [NewsApiService](NewsApiService.md) (8 shared connections)
- [NewsListItem](NewsListItem.md) (5 shared connections)
- [.get_route_handler](get_route_handler.md) (4 shared connections)
- [ai_processor.py](ai_processor.py.md) (3 shared connections)
- [collections_abc](collections_abc.md) (3 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (2 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [.valid_content](valid_content.md) (1 shared connections)
- [test_news_service.py](test_news_service.py.md) (1 shared connections)

## Source Files

- `src/backend/app/api/v1/news.py`
- `src/backend/app/schemas/news.py`
- `tests/backend/tests/unit/api/test_app_news_api.py`

## Audit Trail

- EXTRACTED: 147 (83%)
- INFERRED: 30 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*