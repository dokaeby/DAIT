# canonicalize_url

> 6 nodes

## Key Concepts

- **canonicalize_url()** (5 connections) — `src/backend/src/dait/core/url_safety.py`
- **TestCanonicalize** (3 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **.test_normalizes()** (3 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **dedupe 비교용으로 URL을 정규화한다. 입력: url (검증을 통과한 절대 URL) 출력: str (스킴·호스트 소문자, 기본 포트…** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **canonicalize_url 정규화.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`
- **스킴·호스트 소문자, 기본 포트·fragment 제거.** (1 connections) — `tests/backend/tests/unit/test_url_safety.py`

## Relationships

- [collection_service.py](collection_service.py.md) (2 shared connections)
- [validate_public_https_url](validate_public_https_url.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/url_safety.py`
- `tests/backend/tests/unit/test_url_safety.py`

## Audit Trail

- EXTRACTED: 8 (89%)
- INFERRED: 1 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*