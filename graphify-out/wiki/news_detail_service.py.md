# news_detail_service.py

> 35 nodes

## Key Concepts

- **news_detail_service.py** (21 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **_detail_uncached()** (14 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **get_news_detail()** (11 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **NewsDetailResponse** (8 connections) — `src/backend/src/dait/schemas/news.py`
- **ranking_relation_service.py** (6 connections) — `src/backend/src/dait/services/ranking_relation_service.py`
- **needs_translation()** (5 connections) — `src/backend/src/dait/core/article_language.py`
- **list_related()** (5 connections) — `src/backend/src/dait/services/ranking_relation_service.py`
- **_content_status()** (4 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **_processing_info()** (4 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **test_translation_policy()** (4 connections) — `tests/backend/tests/unit/test_article_language.py`
- **test_article_language.py** (4 connections) — `tests/backend/tests/unit/test_article_language.py`
- **_estimate_read_minutes()** (3 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **article_language.py** (3 connections) — `src/backend/src/dait/core/article_language.py`
- **Settings** (2 connections)
- **ProcessingStatus** (1 connections)
- **DbConnection** (1 connections)
- **parametrize** (1 connections)
- **언어 메타데이터가 없는 기존 기사의 번역 노출 정책.** (1 connections) — `src/backend/src/dait/core/article_language.py`
- **국내 한국어는 제외하며 기존 해외 출처 결과만 제한적으로 복원한다.** (1 connections) — `src/backend/src/dait/core/article_language.py`
- **GET /v1/news/{news_id} 응답.** (1 connections) — `src/backend/src/dait/schemas/news.py`
- **FR-DETAIL-01 뉴스 상세: 저장된 기사·콘텐츠·관계 결과를 계약으로 조립한다.** (1 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **정제 본문 길이로 읽기 시간(분)을 어림한다. 입력: extracted_text (정제된 기사 텍스트, 없을 수 있음) 출력: int 또는…** (1 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **content_results.status를 API 상태로 변환한다.** (1 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **상세의 처리 단계 상태를 만든다. 입력: raw (content_results.status) 출력: ProcessingInfo 기능: 공개…** (1 connections) — `src/backend/src/dait/services/news_detail_service.py`
- **뉴스 상세를 조회한다(캐시 우선). 입력: settings (앱 설정), news_id (경로의 불투명 ID) 출력:…** (1 connections) — `src/backend/src/dait/services/news_detail_service.py`
- *... and 10 more nodes in this community*

## Relationships

- [dait/schemas/news.py](dait-schemas-news.py.md) (14 shared connections)
- [cache_retry_service.py](cache_retry_service.py.md) (6 shared connections)
- [src/backend/src/dait/api/v1/news_routes.py](src-backend-src-dait-api-v1-news_routes.py.md) (4 shared connections)
- [NewsCategory](NewsCategory.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/article_language.py`
- `src/backend/src/dait/schemas/news.py`
- `src/backend/src/dait/services/news_detail_service.py`
- `src/backend/src/dait/services/ranking_relation_service.py`
- `tests/backend/tests/unit/test_article_language.py`

## Audit Trail

- EXTRACTED: 68 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*