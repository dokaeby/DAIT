# fetch_public_bytes

> 26 nodes

## Key Concepts

- **fetch_public_bytes()** (16 connections) — `src/backend/src/dait/core/url_safety.py`
- **TestFetch** (10 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **._client()** (9 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **public_resolver()** (8 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_disallowed_content_type()** (7 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_oversize_body()** (7 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_redirect_to_private_is_blocked()** (7 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_fetch_ok()** (6 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_http_error_status()** (6 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **handler()** (5 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **handler()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **handler()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **handler()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **handler()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **resolver()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **Client** (1 connections)
- **Client** (1 connections)
- **Request** (1 connections)
- **Response** (1 connections)
- **공인 HTTPS URL의 본문을 크기 제한과 함께 가져온다. 입력: client (httpx.Client), url (시작 URL),…** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **공인 URL이 사설 주소로 리다이렉트하면 두 번째 홉에서 거부된다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **html·json 등 허용 목록 밖 형식은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **max_bytes를 넘는 본문은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **테스트용 DNS: 어떤 호스트든 공인 IP로 해석한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **fetch_public_bytes: 리다이렉트·형식·크기 제한.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- *... and 1 more nodes in this community*

## Relationships

- [validate_public_https_url](validate_public_https_url.md) (6 shared connections)
- [collection_service.py](collection_service.py.md) (4 shared connections)
- [robots_service.py](robots_service.py.md) (3 shared connections)
- [test_pipeline_safety.py](test_pipeline_safety.py.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/url_safety.py`
- `tests/backend/tests/unit/test_url_safety.py`

## Audit Trail

- EXTRACTED: 37 (66%)
- INFERRED: 19 (34%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*