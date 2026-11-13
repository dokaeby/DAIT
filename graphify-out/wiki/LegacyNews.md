# LegacyNews

> 12 nodes

## Key Concepts

- **LegacyNews** (9 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **legacy_news.py** (6 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **.https_only()** (4 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **.utc_timestamp()** (4 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **datetime** (2 connections)
- **field_validator** (2 connections)
- **BaseModel** (1 connections)
- **HttpUrl** (1 connections)
- **기존 수집 결과를 통합 저장소로 옮기는 검증 모델.** (1 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **기존 DB의 성공 결과만 받는다. 기존 SQLite의 UTC 시각을 명시한다.** (1 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **기존 수집 DB의 naive UTC 저장 형식을 복원한다.** (1 connections) — `src/backend/src/dait/schemas/legacy_news.py`
- **통합 API의 HTTPS 공개 조건을 유지한다.** (1 connections) — `src/backend/src/dait/schemas/legacy_news.py`

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [legacy_news_service.py](legacy_news_service.py.md) (2 shared connections)
- [test_legacy_news.py](test_legacy_news.py.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/schemas/legacy_news.py`

## Audit Trail

- EXTRACTED: 17 (85%)
- INFERRED: 3 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*