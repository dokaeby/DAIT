# backend/tests/unit/test_app_http.py

> 42 nodes

## Key Concepts

- **backend/tests/unit/test_app_http.py** (24 connections) — `tests/backend/tests/unit/test_app_http.py`
- **make_client()** (18 connections) — `tests/backend/tests/unit/test_app_http.py`
- **Path** (15 connections)
- **test_bad_request_id_is_replaced()** (5 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_unhandled_error_is_generic_500()** (5 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_validation_error_does_not_echo_input()** (5 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_cors_allows_only_listed_origin()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_debug_has_docs()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_healthz_ok()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_keepalive_ok_even_when_db_down()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_readyz_db_down_returns_503_without_path()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_readyz_ok()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_release_has_no_docs()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_request_id_in_header_and_body()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_valid_request_id_is_kept()** (4 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_oversized_body_returns_413()** (3 connections) — `tests/backend/tests/unit/test_app_http.py`
- **test_security_headers_present()** (3 connections) — `tests/backend/tests/unit/test_app_http.py`
- **boom()** (1 connections) — `tests/backend/tests/unit/test_app_http.py`
- **echo()** (1 connections) — `tests/backend/tests/unit/test_app_http.py`
- **AppEnv** (1 connections)
- **HttpClient** (1 connections)
- **MonkeyPatch** (1 connections)
- **parametrize** (1 connections)
- **앱 조립 결과 테스트: 헬스체크, request_id, 오류 형식, 보안 헤더, 모드별 문서 경로.** (1 connections) — `tests/backend/tests/unit/test_app_http.py`
- **release에서는 docs/redoc/openapi가 404다.** (1 connections) — `tests/backend/tests/unit/test_app_http.py`
- *... and 17 more nodes in this community*

## Relationships

- [pytest](pytest.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [datetime](datetime.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_app_http.py`

## Audit Trail

- EXTRACTED: 69 (97%)
- INFERRED: 2 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*