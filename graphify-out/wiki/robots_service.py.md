# robots_service.py

> 21 nodes

## Key Concepts

- **robots_service.py** (18 connections) — `src/backend/src/dait/services/robots_service.py`
- **UnsafeUrlError** (11 connections) — `src/backend/src/dait/core/url_safety.py`
- **_load_rules()** (10 connections) — `src/backend/src/dait/services/robots_service.py`
- **check_robots()** (6 connections) — `src/backend/src/dait/services/robots_service.py`
- **_default_fetch()** (4 connections) — `src/backend/src/dait/services/robots_service.py`
- **_parse()** (4 connections) — `src/backend/src/dait/services/robots_service.py`
- **robots_url()** (3 connections) — `src/backend/src/dait/services/robots_service.py`
- **clear_cache()** (2 connections) — `src/backend/src/dait/services/robots_service.py`
- **FetchFn** (2 connections)
- **Exception** (2 connections)
- **Resolver** (2 connections)
- **urllib_robotparser** (2 connections)
- **RobotFileParser** (1 connections)
- **허용되지 않은 URL·사설 주소 등 안전하지 않은 대상.** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **robots.txt 확인: 수집 전 대상 사이트의 크롤 허용 규칙을 읽는다 (FR-PIPE-01).** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **메모리 캐시를 비운다. 테스트와 설정 변경 시 호출한다.** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **출처 base_url에서 robots.txt URL을 만든다. 입력: base_url (예: https://example.com/feed)…** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **robots.txt 본문을 RobotFileParser로 파싱한다.** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **실제 안전 fetch로 robots.txt를 가져온다. 404는 None이 아니라 표시용 예외 없이 구분한다.** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **robots 규칙을 캐시와 함께 불러온다. 출력: RobotFileParser | _ALLOW_ALL | _UNAVAILABLE** (1 connections) — `src/backend/src/dait/services/robots_service.py`
- **대상 URL을 현재 User-Agent로 가져와도 되는지 robots.txt로 판정한다. 입력: base_url (출처 기준 URL),…** (1 connections) — `src/backend/src/dait/services/robots_service.py`

## Relationships

- [collection_service.py](collection_service.py.md) (9 shared connections)
- [collections_abc](collections_abc.md) (3 shared connections)
- [fetch_public_bytes](fetch_public_bytes.md) (3 shared connections)
- [validate_public_https_url](validate_public_https_url.md) (3 shared connections)
- [test_pipeline_safety.py](test_pipeline_safety.py.md) (2 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [db_search.py](db_search.py.md) (1 shared connections)
- [CollectorSource](CollectorSource.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/url_safety.py`
- `src/backend/src/dait/services/robots_service.py`

## Audit Trail

- EXTRACTED: 41 (84%)
- INFERRED: 8 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*