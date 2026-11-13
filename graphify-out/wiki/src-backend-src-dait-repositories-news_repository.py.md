# src/backend/src/dait/repositories/news_repository.py

> 37 nodes

## Key Concepts

- **src/backend/src/dait/repositories/news_repository.py** (22 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **DbConnection** (10 connections)
- **list_public_news()** (6 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **_public_status_clause()** (6 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **NewsListRow** (5 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **count_public_news()** (5 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **get_public_news()** (5 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **list_related_news()** (5 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **NewsDetailRow** (4 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **_escape_like()** (4 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **insert_news()** (4 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **insert_pending_content()** (4 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **RelatedRow** (3 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **find_id_by_canonical_url()** (3 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **find_id_by_content_hash()** (3 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **has_recent_job_failures()** (3 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **list_enabled_source_ids()** (3 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **datetime** (3 connections)
- **NamedTuple** (3 connections)
- **parse_summary_lines()** (2 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **news·sources·content_results·news_relations 조회. 공개 목록·상세·관련 뉴스를 담당한다.** (1 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **현재 조건에서 화면에 표시 가능한 전체 건수를 센다. 입력: conn (연결), category, query (정규화된 검색어) 출력: int…** (1 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **목록 조회 한 행: 카드 표시와 정렬에 필요한 값만 담는다.** (1 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **최근 작업 실패가 있는지 확인한다(목록의 partial 표시용). 입력: conn (연결), since_iso (기준 시각 ISO 문자열)…** (1 connections) — `src/backend/src/dait/repositories/news_repository.py`
- **공개 가능한 뉴스 한 건의 상세 행을 조회한다. 입력: conn (연결), news_id (불투명 뉴스 ID) 출력: NewsDetailRow…** (1 connections) — `src/backend/src/dait/repositories/news_repository.py`
- *... and 12 more nodes in this community*

## Relationships

- [dait/schemas/news.py](dait-schemas-news.py.md) (2 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/news_repository.py`

## Audit Trail

- EXTRACTED: 62 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*