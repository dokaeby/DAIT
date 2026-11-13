# backend/tests/unit/test_config.py

> 25 nodes

## Key Concepts

- **backend/tests/unit/test_config.py** (16 connections) — `tests/backend/tests/unit/test_config.py`
- **MonkeyPatch** (11 connections)
- **test_cors_wildcard_and_non_http_rejected()** (4 connections) — `tests/backend/tests/unit/test_config.py`
- **test_supported_database_urls_pass()** (4 connections) — `tests/backend/tests/unit/test_config.py`
- **test_default_is_release()** (3 connections) — `tests/backend/tests/unit/test_config.py`
- **test_short_jwt_secret_is_rejected()** (3 connections) — `tests/backend/tests/unit/test_config.py`
- **test_token_lifetime_defaults_and_bounds()** (3 connections) — `tests/backend/tests/unit/test_config.py`
- **test_unknown_app_env_is_rejected()** (3 connections) — `tests/backend/tests/unit/test_config.py`
- **test_unknown_database_url_scheme_is_rejected()** (3 connections) — `tests/backend/tests/unit/test_config.py`
- **test_cors_valid_origin_passes()** (2 connections) — `tests/backend/tests/unit/test_config.py`
- **test_docs_enabled_only_in_debug()** (2 connections) — `tests/backend/tests/unit/test_config.py`
- **test_jwt_secret_never_appears_in_repr_or_dump()** (2 connections) — `tests/backend/tests/unit/test_config.py`
- **test_missing_jwt_secret_is_rejected()** (2 connections) — `tests/backend/tests/unit/test_config.py`
- **test_settings_are_frozen()** (2 connections) — `tests/backend/tests/unit/test_config.py`
- **parametrize** (2 connections)
- **core/config 설정 검증 테스트 (시작 거부, 기본값, 불변성).** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **APP_ENV 기본값은 release다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **알 수 없는 APP_ENV는 시작을 거부한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **지원하지 않는 DB 스킴의 DATABASE_URL은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **sqlite(로컬)와 postgresql/postgres(서버) URL은 허용한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **CORS 와일드카드와 http(s) 아닌 값은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **서명 키가 32자보다 짧으면 시작을 거부한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **서명 키는 repr, 문자열, JSON 덤프 어디에도 나오지 않는다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **토큰 수명 기본값은 15분·14일이고 범위를 벗어나면 거부한다.** (1 connections) — `tests/backend/tests/unit/test_config.py`
- **ambiguous_python_import_484bad7e5c29** (1 connections)

## Relationships

- [pytest](pytest.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_config.py`

## Audit Trail

- EXTRACTED: 37 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*