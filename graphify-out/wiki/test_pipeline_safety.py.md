# test_pipeline_safety.py

> 36 nodes

## Key Concepts

- **test_pipeline_safety.py** (17 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **make_fetcher()** (11 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **FetchedBody** (10 connections) — `src/backend/src/dait/core/url_safety.py`
- **public_resolver()** (10 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **TestCollection** (9 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **Settings** (7 connections)
- **TestRobots** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **seed_source()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_collects_and_dedupes()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_content_dedupe_across_urls()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_fetch_failure_records_job_attempt()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_non_https_and_bad_links_rejected()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_robots_disallow_skips_source()** (6 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_unavailable_is_conservative_deny()** (5 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **fetch()** (4 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_allow_when_no_robots()** (4 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_disallow_blocks()** (4 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **_clean_caches()** (3 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **fetch()** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **fixture** (1 connections)
- **robots·수집·잡·캐시 안전장치 테스트. 네트워크는 전부 fake로 대체한다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **collection_service.run_collection.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **피드를 수집해 PENDING 기사로 저장하고, 같은 시간 창 재실행은 SKIPPED.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **http 링크는 거부되고 https 정상 항목만 저장된다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **URL이 달라도 제목+요약이 같으면 중복으로 센다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- *... and 11 more nodes in this community*

## Relationships

- [collection_service.py](collection_service.py.md) (6 shared connections)
- [datetime](datetime.md) (4 shared connections)
- [TestCacheRetry](TestCacheRetry.md) (3 shared connections)
- [robots_service.py](robots_service.py.md) (2 shared connections)
- [fetch_public_bytes](fetch_public_bytes.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [validate_public_https_url](validate_public_https_url.md) (1 shared connections)
- [TestJobRepository](TestJobRepository.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/url_safety.py`
- `tests/backend/tests/unit/test_pipeline_safety.py`

## Audit Trail

- EXTRACTED: 62 (76%)
- INFERRED: 20 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*