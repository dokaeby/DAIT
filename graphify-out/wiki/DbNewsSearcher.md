# DbNewsSearcher

> 20 nodes

## Key Concepts

- **DbNewsSearcher** (10 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **CompareTests** (8 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **FlakySearcher** (8 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **.search()** (7 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **SearchHit** (6 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **.search()** (5 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **.search()** (5 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **DbConnection** (3 connections)
- **.test_cpu_model_load_and_version_identity()** (2 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.test_display_scores_include_keyword_below_threshold()** (2 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.__init__()** (2 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **.test_e5_input_prefixes()** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.test_embedding_response_contract()** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.test_hybrid_ranking()** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.test_keyword_and_cache_invalidation()** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **.test_vectors_and_cosine()** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- **DbConnection** (1 connections)
- **검색 결과 기사 한 건(검색 구현과 무관한 공통 형태).** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **조건에 맞는 기사를 최신순으로 limit건까지 돌려준다. 실패하면 예외를 올린다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **이미 수집·요약된 뉴스에서 예약 조건으로 찾는 임시 검색기. 키워드가 여러 개면 하나라도 제목·요약에 들어 있는 기사를 모은다(OR).…** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`

## Relationships

- [NewsCategory](NewsCategory.md) (5 shared connections)
- [test_schedule_runs.py](test_schedule_runs.py.md) (5 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (3 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (3 shared connections)
- [dait/services/search_lab_service.py](dait-services-search_lab_service.py.md) (2 shared connections)
- [src/backend/src/dait/api/v1/news_routes.py](src-backend-src-dait-api-v1-news_routes.py.md) (1 shared connections)

## Source Files

- `docs/demo/DAIT_ui_v1.0.1/tests/test_compare.py`
- `src/backend/src/dait/services/schedule_run_service.py`
- `tests/backend/tests/unit/test_schedule_runs.py`

## Audit Trail

- EXTRACTED: 33 (77%)
- INFERRED: 10 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*