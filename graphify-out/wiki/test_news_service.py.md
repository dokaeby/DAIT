# test_news_service.py

> 44 nodes

## Key Concepts

- **test_news_service.py** (71 connections) — `tests/backend/tests/unit/test_news_service.py`
- **news()** (65 connections) — `tests/backend/tests/unit/test_news_service.py`
- **FakeRepository** (36 connections) — `tests/backend/tests/unit/test_news_service.py`
- **FakeCache** (35 connections) — `tests/backend/tests/unit/test_news_service.py`
- **service()** (32 connections) — `tests/backend/tests/unit/test_news_service.py`
- **asyncio** (27 connections)
- **NewsServicePolicy** (14 connections) — `src/backend/app/services/news_service.py`
- **SourcePriority** (11 connections) — `src/backend/app/services/news_service.py`
- **test_config_order_shares_cache_but_priority_change_isolated()** (10 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_ranked_list_slicing_and_cache_hit()** (9 connections) — `tests/backend/tests/unit/test_news_service.py`
- **_stored_midterms_mistranslation()** (8 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_list_redis_failures_fall_back_to_db()** (8 connections) — `tests/backend/tests/unit/test_news_service.py`
- **policy()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_db_snapshot_preceding_commit_cannot_refill_invalidated_generation()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_detail_redis_failures_fall_back_to_db()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_existing_db_title_is_corrected_using_stored_summary_without_retranslation()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_missing_source_priority_is_not_invented()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_only_successful_ready_commit_invalidates()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_redis_timeouts_are_bounded_and_do_not_fail_response()** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_corrupt_and_wrong_limit_list_cache_are_ignored()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_corrupt_wrong_id_and_invalid_summary_detail_cache_are_ignored()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_db_failure_propagates_instead_of_returning_fake_empty_list()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_detail_cache_hit_and_ttl()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_detail_missing_is_not_negative_cached()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_empty_list_and_insufficient_detail()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- *... and 19 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (17 shared connections)
- [news_service.py](news_service.py.md) (14 shared connections)
- [DAIT 개별 기능별 상세 설계서](DAIT_개별_기능별_상세_설계서.md) (12 shared connections)
- [.check](check.md) (9 shared connections)
- [StoredNews](StoredNews.md) (9 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (7 shared connections)
- [test_ranking_service.py](test_ranking_service.py.md) (6 shared connections)
- [FakeRedisWire](FakeRedisWire.md) (6 shared connections)
- [.list_candidates](list_candidates.md) (4 shared connections)
- [.category](category.md) (4 shared connections)
- [07_DB_설계서_v1.0.1.md](07_DB_설계서_v1.0.1.md.md) (4 shared connections)
- [07_DB_설계서_v1.0.2.md](07_DB_설계서_v1.0.2.md.md) (4 shared connections)

## Source Files

- `src/backend/app/services/news_service.py`
- `tests/backend/tests/unit/test_news_service.py`

## Audit Trail

- EXTRACTED: 253 (82%)
- INFERRED: 57 (18%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*