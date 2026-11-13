# validate_public_https_url

> 22 nodes

## Key Concepts

- **validate_public_https_url()** (13 connections) — `src/backend/src/dait/core/url_safety.py`
- **test_url_safety.py** (10 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **TestValidateUrl** (7 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_rejects_unsafe()** (5 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_accepts_public_https()** (4 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_rejects_private_dns_result()** (4 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_rejects_unresolvable()** (4 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **_is_blocked_ip()** (3 connections) — `src/backend/src/dait/core/url_safety.py`
- **private_resolver()** (3 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **Resolver** (2 connections)
- **dait_core_url_safety** (2 connections)
- **failing()** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **parametrize** (1 connections)
- **IP 문자열이 차단 대상인지 확인한다. 입력: raw (IPv4/IPv6 주소 문자열) 출력: bool 기능:…** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **URL이 공인 HTTPS 주소인지 검증하고 DNS 결과까지 확인한다. 입력: url (검사할 절대 URL), resolver (테스트용 IP…** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **SSRF·안전 fetch 테스트. 모든 네트워크는 httpx.MockTransport로 대체한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **테스트용 DNS: 사설 IP로 해석한다(rebinding·내부 호스트 흉내).** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **validate_public_https_url 규칙.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **http·자격증명·사설 IP 리터럴·IPv6 사설 주소는 거부된다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **호스트명이 사설 IP로 해석되면 거부한다(DNS 기반 SSRF).** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **DNS 해석 실패는 안전하지 않다고 거부한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **공인 IP로 해석되는 https는 통과한다.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`

## Relationships

- [fetch_public_bytes](fetch_public_bytes.md) (6 shared connections)
- [robots_service.py](robots_service.py.md) (3 shared connections)
- [collections_abc](collections_abc.md) (3 shared connections)
- [collection_service.py](collection_service.py.md) (2 shared connections)
- [CollectionResult](CollectionResult.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [canonicalize_url](canonicalize_url.md) (1 shared connections)
- [test_pipeline_safety.py](test_pipeline_safety.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/url_safety.py`
- `tests/backend/tests/unit/test_url_safety.py`

## Audit Trail

- EXTRACTED: 34 (79%)
- INFERRED: 9 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*