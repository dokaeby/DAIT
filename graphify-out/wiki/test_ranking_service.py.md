# test_ranking_service.py

> 59 nodes

## Key Concepts

- **test_ranking_service.py** (40 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **RankingRequest** (35 connections) — `src/backend/app/services/ranking_service.py`
- **RankingService** (25 connections) — `src/backend/app/services/ranking_service.py`
- **candidate()** (25 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **RankingCandidate** (23 connections) — `src/backend/app/services/ranking_service.py`
- **.rank()** (20 connections) — `src/backend/app/services/ranking_service.py`
- **ranking_service.py** (19 connections) — `src/backend/app/services/ranking_service.py`
- **RankedNews** (11 connections) — `src/backend/app/services/ranking_service.py`
- **ranked_ids()** (11 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_weighted_ranking_combines_recency_priority_keywords_and_popularity()** (8 connections) — `tests/backend/tests/unit/test_taxonomy_and_categories.py`
- **SpyRanking** (7 connections) — `tests/backend/tests/unit/test_news_service.py`
- **.calculate_weighted_score()** (7 connections) — `src/backend/app/services/ranking_service.py`
- **.order()** (7 connections) — `src/backend/app/services/ranking_service.py`
- **test_entire_batch_is_sorted_before_slicing()** (7 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_short_input_is_returned_without_padding()** (7 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **RankingModel** (6 connections) — `src/backend/app/services/ranking_service.py`
- **compute_keyword_and_popularity()** (6 connections) — `src/backend/app/services/ranking_service.py`
- **test_all_input_permutations_produce_identical_output()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_constructed_request_is_revalidated_at_service_boundary()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_equal_instants_in_different_timezones_use_id_tie_break()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_extreme_dates_preserve_microsecond_precision()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_newer_publication_overrides_source_priority_and_id()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_rank_does_not_depend_on_wall_clock_or_randomness()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_ready_overrides_recency_source_priority_and_id()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- **test_source_priority_overrides_id_when_quality_and_time_tie()** (6 connections) — `tests/backend/tests/unit/test_ranking_service.py`
- *... and 34 more nodes in this community*

## Relationships

- [news_service.py](news_service.py.md) (15 shared connections)
- [ai_processor.py](ai_processor.py.md) (13 shared connections)
- [test_news_service.py](test_news_service.py.md) (6 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (6 shared connections)
- [NewsCache](NewsCache.md) (4 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (4 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [.unique_ids](unique_ids.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [no_network](no_network.md) (1 shared connections)

## Source Files

- `src/backend/app/services/news_service.py`
- `src/backend/app/services/ranking_service.py`
- `tests/backend/tests/unit/test_news_service.py`
- `tests/backend/tests/unit/test_ranking_service.py`
- `tests/backend/tests/unit/test_taxonomy_and_categories.py`

## Audit Trail

- EXTRACTED: 191 (84%)
- INFERRED: 36 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*