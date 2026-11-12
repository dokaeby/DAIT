# src/backend/src/dait/api/v1/news_routes.py

> 40 nodes

## Key Concepts

- **src/backend/src/dait/api/v1/news_routes.py** (20 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **list_news()** (16 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **news_activity()** (12 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **news_activity_service.py** (11 connections) — `src/backend/src/dait/services/news_activity_service.py`
- **mark_news_read()** (9 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **normalize_query()** (7 connections) — `src/backend/src/dait/services/news_search_service.py`
- **news_detail()** (6 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **activity()** (6 connections) — `src/backend/src/dait/services/news_activity_service.py`
- **news_search_service.py** (5 connections) — `src/backend/src/dait/services/news_search_service.py`
- **mark_read()** (4 connections) — `src/backend/src/dait/services/news_activity_service.py`
- **SettingsDep** (4 connections)
- **Depends** (3 connections)
- **get** (3 connections)
- **UserRecord** (3 connections)
- **get_current_user** (2 connections)
- **max_length** (2 connections)
- **Query** (2 connections)
- **Response** (2 connections)
- **Settings** (2 connections)
- **ge** (1 connections)
- **le** (1 connections)
- **get_optional_user** (1 connections)
- **SortOrder** (1 connections)
- **FR-HOME-01/02, FR-SEARCH-01, FR-DETAIL-01~02 뉴스 API. 목록·검색·상세는 저장 결과만 반환하며 조회 시…** (1 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- **공개 가능한 기사를 랭킹순/최신순으로 조회한다. 입력: category(AI만 활성), q(제목+검증된 요약 검색), sort,…** (1 connections) — `src/backend/src/dait/api/v1/news_routes.py`
- *... and 15 more nodes in this community*

## Relationships

- [dait/schemas/news.py](dait-schemas-news.py.md) (14 shared connections)
- [news_detail_service.py](news_detail_service.py.md) (4 shared connections)
- [NewsCategory](NewsCategory.md) (2 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [DAIT_ui_v1.0.1/src/backend/src/dait/api/v1/settings_routes.py](DAIT_ui_v1.0.1-src-backend-src-dait-api-v1-settings_routes.py.md) (1 shared connections)
- [DbNewsSearcher](DbNewsSearcher.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/news_routes.py`
- `src/backend/src/dait/services/news_activity_service.py`
- `src/backend/src/dait/services/news_search_service.py`

## Audit Trail

- EXTRACTED: 79 (95%)
- INFERRED: 4 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*