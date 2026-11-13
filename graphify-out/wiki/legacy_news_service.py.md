# legacy_news_service.py

> 14 nodes

## Key Concepts

- **legacy_news_service.py** (8 connections) — `src/backend/src/dait/services/legacy_news_service.py`
- **insert_result()** (7 connections) — `src/backend/src/dait/repositories/legacy_news_repository.py`
- **import_saved_news()** (7 connections) — `src/backend/src/dait/services/legacy_news_service.py`
- **read_results()** (6 connections) — `src/backend/src/dait/repositories/legacy_news_repository.py`
- **lifespan()** (2 connections) — `src/backend/src/dait/main.py`
- **DbConnection** (1 connections)
- **Path** (1 connections)
- **Settings** (1 connections)
- **개인 DB나 토큰은 읽지 않고 성공한 기사만 모델로 검증한다.** (1 connections) — `src/backend/src/dait/repositories/legacy_news_repository.py`
- **URL 기준 멱등 삽입으로 기존 계정과 이미 저장된 기사를 보존한다.** (1 connections) — `src/backend/src/dait/repositories/legacy_news_repository.py`
- **서버 시작 준비 단계에서 기존 공용 결과를 통합 DB에 연결한다.** (1 connections) — `src/backend/src/dait/services/legacy_news_service.py`
- **원본이 있을 때만 처리한다. 조회 요청에서는 수집·LLM을 호출하지 않는다.** (1 connections) — `src/backend/src/dait/services/legacy_news_service.py`
- **ambiguous_python_import_59974db4d890** (1 connections)
- **ambiguous_python_import_d7c9aaef5f08** (1 connections)

## Relationships

- [src/backend/src/dait/main.py](src-backend-src-dait-main.py.md) (3 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [LegacyNews](LegacyNews.md) (2 shared connections)
- [test_legacy_news.py](test_legacy_news.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/main.py`
- `src/backend/src/dait/repositories/legacy_news_repository.py`
- `src/backend/src/dait/services/legacy_news_service.py`

## Audit Trail

- EXTRACTED: 19 (79%)
- INFERRED: 5 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*