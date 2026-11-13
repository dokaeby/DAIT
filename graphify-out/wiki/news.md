# news()

> God node · 65 connections · `tests/backend/tests/unit/test_news_service.py`

**Community:** [test_news_service.py](test_news_service.py.md)

## Connections by Relation

### calls
- [CollectedArticle](CollectedArticle.md) `EXTRACTED`
- [SuccessContent](SuccessContent.md) `EXTRACTED`
- [StoredNews](StoredNews.md) `EXTRACTED`
- InsufficientContent `EXTRACTED`
- PipelineRecord `EXTRACTED`
- test_config_order_shares_cache_but_priority_change_isolated() `EXTRACTED`
- test_ranked_list_slicing_and_cache_hit() `EXTRACTED`
- _stored_midterms_mistranslation() `EXTRACTED`
- test_list_redis_failures_fall_back_to_db() `EXTRACTED`
- test_db_snapshot_preceding_commit_cannot_refill_invalidated_generation() `EXTRACTED`
- test_detail_redis_failures_fall_back_to_db() `EXTRACTED`
- test_missing_source_priority_is_not_invented() `EXTRACTED`
- test_only_successful_ready_commit_invalidates() `EXTRACTED`
- test_redis_timeouts_are_bounded_and_do_not_fail_response() `EXTRACTED`
- test_corrupt_and_wrong_limit_list_cache_are_ignored() `EXTRACTED`
- test_corrupt_wrong_id_and_invalid_summary_detail_cache_are_ignored() `EXTRACTED`
- test_detail_cache_hit_and_ttl() `EXTRACTED`
- test_detail_missing_is_not_negative_cached() `EXTRACTED`
- test_empty_list_and_insufficient_detail() `EXTRACTED`
- test_invalid_generation_falls_back_without_cache_write() `EXTRACTED`
- *…and 8 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- [test_news_service.py](test_news_service.py.md) `EXTRACTED`

### indirect_call
- isolated_runtime() `INFERRED`

### references
- 3A.1 구현 테이블 목록 (18개, `alembic_version` 포함 17개 업무 테이블) `INFERRED`
- 6. FR-HOME-01 랭킹 카드 `INFERRED`
- 6. FR-HOME-01 랭킹 카드 `INFERRED`
- 6. FR-HOME-01 랭킹 카드 `INFERRED`
- 3.7 `news` `INFERRED`
- 6. FR-HOME-01 랭킹 카드 `INFERRED`
- 3.7 `news` `INFERRED`
- 3.7 `news` `INFERRED`
- 14. FR-PIPE-01 수집 `INFERRED`
- 16. FR-PIPE-03 랭킹과 관련 뉴스 `INFERRED`
- 9. FR-DETAIL-01 상세 콘텐츠 `INFERRED`
- 14. FR-PIPE-01 수집 `INFERRED`
- 16. FR-PIPE-03 랭킹과 관련 뉴스 `INFERRED`
- 9. FR-DETAIL-01 상세 콘텐츠 `INFERRED`
- 14. FR-PIPE-01 수집 `INFERRED`
- 16. FR-PIPE-03 랭킹과 관련 뉴스 `INFERRED`
- 9. FR-DETAIL-01 상세 콘텐츠 `INFERRED`
- 14. FR-PIPE-01 수집 `INFERRED`
- 16. FR-PIPE-03 랭킹과 관련 뉴스 `INFERRED`
- 9. FR-DETAIL-01 상세 콘텐츠 `INFERRED`
- *…and 15 more `references` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*