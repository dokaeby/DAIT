# _ManagedRuntime

> 37 nodes

## Key Concepts

- **_ManagedRuntime** (39 connections) — `src/backend/app/api/main.py`
- **Project_DAIT 개발 인수인계서 (Handover Document)** (12 connections) — `HANDOVER.md`
- **2026-11-12 뉴스 파이프라인 정정 사항** (10 connections) — `HANDOVER.md`
- **._bootstrap_if_empty()** (6 connections) — `src/backend/app/api/main.py`
- **._is_invalid_record()** (6 connections) — `src/backend/app/api/main.py`
- **._crawl_and_invalidate()** (5 connections) — `src/backend/app/api/main.py`
- **._reprocess_fallbacks()** (5 connections) — `src/backend/app/api/main.py`
- **.startup()** (5 connections) — `src/backend/app/api/main.py`
- **._crawl_official_rss_feeds()** (4 connections) — `src/backend/app/api/main.py`
- **.query_news()** (4 connections) — `src/backend/app/api/main.py`
- **.refresh()** (4 connections) — `src/backend/app/api/main.py`
- **._schedule_crawl()** (4 connections) — `src/backend/app/api/main.py`
- **3. 최근 주요 수정 및 고도화 이력 (상세)** (4 connections) — `HANDOVER.md`
- **4. 프론트엔드 및 API 엔드포인트 호출 규격 요약** (4 connections) — `HANDOVER.md`
- **리뷰 후속 수정 — 검색 정확성 + 운영 효율 (2026-11-12 추가)** (4 connections) — `HANDOVER.md`
- **스키마 리셋 → 타겟 삭제로 교체 (`api/main.py`, `repositories/news_repository.py`)** (4 connections) — `HANDOVER.md`
- **._collect_loop()** (3 connections) — `src/backend/app/api/main.py`
- **.get_api_detail()** (3 connections) — `src/backend/app/api/main.py`
- **._reset_schema_and_data()** (2 connections) — `src/backend/app/api/main.py`
- **1. 프로젝트 핵심 개발 원칙 (절대 위반 금지)** (2 connections) — `HANDOVER.md`
- **3.1 개별 기사 상세 URL(`canonical_url` / `original_url`) 정상화 및 더미 데이터 영구 제거** (2 connections) — `HANDOVER.md`
- **3.3 구글 번역(`deep-translator`) 연동 및 해외 기사 제목·요약 표시 방식 개편** (2 connections) — `HANDOVER.md`
- **4.2 뉴스 상세 조회: `GET /v1/news/{news_id}`** (2 connections) — `HANDOVER.md`
- **번역 실패 기사 저장 차단 (`workers/ai_processor.py`)** (2 connections) — `HANDOVER.md`
- **.is_collecting()** (1 connections) — `src/backend/app/api/main.py`
- *... and 12 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (9 shared connections)
- [news_service.py](news_service.py.md) (8 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (5 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (4 shared connections)
- [StoredNews](StoredNews.md) (4 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (3 shared connections)
- [CollectionResult](CollectionResult.md) (3 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (2 shared connections)
- [unit/test_collector.py](unit-test_collector.py.md) (2 shared connections)
- [test_app_news_api.py](test_app_news_api.py.md) (2 shared connections)
- [NewsApiService](NewsApiService.md) (1 shared connections)
- [NewsCache](NewsCache.md) (1 shared connections)

## Source Files

- `HANDOVER.md`
- `src/backend/app/api/main.py`

## Audit Trail

- EXTRACTED: 68 (67%)
- INFERRED: 33 (33%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*