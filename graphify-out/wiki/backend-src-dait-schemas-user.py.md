# backend/src/dait/schemas/user.py

> 12 nodes

## Key Concepts

- **backend/src/dait/schemas/user.py** (9 connections) — `src/backend/src/dait/schemas/user.py`
- **UserPublic** (3 connections) — `src/backend/src/dait/schemas/user.py`
- **UserRecord** (3 connections) — `src/backend/src/dait/schemas/user.py`
- **UserRole** (3 connections) — `src/backend/src/dait/schemas/user.py`
- **UserStatus** (3 connections) — `src/backend/src/dait/schemas/user.py`
- **BaseModel** (2 connections)
- **StrEnum** (2 connections)
- **사용자 모델: DB에서 읽는 레코드와 응답용 공개 모델을 분리한다.** (1 connections) — `src/backend/src/dait/schemas/user.py`
- **계정 상태. 지금은 정상 계정만 있다.** (1 connections) — `src/backend/src/dait/schemas/user.py`
- **역할. 모든 보호 라우트는 기본 거부이고 이 값으로 허용 범위를 정한다.** (1 connections) — `src/backend/src/dait/schemas/user.py`
- **users 테이블 한 행. 비밀번호 해시는 repr·로그에 나오지 않게 한다.** (1 connections) — `src/backend/src/dait/schemas/user.py`
- **응답에 내보내는 사용자 정보. 해시 같은 내부 값은 없다.** (1 connections) — `src/backend/src/dait/schemas/user.py`

## Relationships

- [datetime](datetime.md) (1 shared connections)
- [enum](enum.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [me_routes.py](me_routes.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/schemas/user.py`

## Audit Trail

- EXTRACTED: 17 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*