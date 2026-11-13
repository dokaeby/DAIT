# backend/src/dait/schemas/token.py

> 6 nodes

## Key Concepts

- **backend/src/dait/schemas/token.py** (5 connections) — `src/backend/src/dait/schemas/token.py`
- **StoredRefreshToken** (3 connections) — `src/backend/src/dait/schemas/token.py`
- **RefreshTokenRecord** (2 connections) — `src/backend/src/dait/schemas/token.py`
- **BaseModel** (2 connections)
- **refresh_tokens 테이블 한 행 모델. 토큰 원문은 어디에도 두지 않고 해시만 가진다.** (1 connections) — `src/backend/src/dait/schemas/token.py`
- **DB에서 읽은 refresh 토큰 상태. 회전·재사용 판단에만 쓴다.** (1 connections) — `src/backend/src/dait/schemas/token.py`

## Relationships

- [datetime](datetime.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/schemas/token.py`

## Audit Trail

- EXTRACTED: 8 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*