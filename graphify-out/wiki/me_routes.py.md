# me_routes.py

> 23 nodes

## Key Concepts

- **me_routes.py** (16 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **nickname.py** (14 connections) — `src/backend/src/dait/schemas/nickname.py`
- **NicknameAvailability** (8 connections) — `src/backend/src/dait/schemas/nickname.py`
- **NicknameResult** (7 connections) — `src/backend/src/dait/schemas/nickname.py`
- **NicknameUpdate** (6 connections) — `src/backend/src/dait/schemas/nickname.py`
- **3.7 PATCH `/v1/me/nickname`** (4 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **BaseModel** (3 connections)
- **unicodedata** (3 connections)
- **.empty_to_none()** (2 connections) — `src/backend/src/dait/schemas/nickname.py`
- **normalize_nickname()** (2 connections) — `src/backend/src/dait/schemas/nickname.py`
- **Request (`NicknameUpdate`)** (2 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **Response 200 (`NicknameResult`)** (2 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **field_validator** (1 connections)
- **목적** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **내 계정 라우트(/v1/me). 사용자 id는 항상 토큰에서만 얻고 경로로 받지 않는다.** (1 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **닉네임의 표시값과 중복 비교 규칙을 공유한다.** (1 connections) — `src/backend/src/dait/schemas/nickname.py`
- **호환 문자와 앞뒤 공백을 정규화하고 제어문자를 거부한다.** (1 connections) — `src/backend/src/dait/schemas/nickname.py`
- **닉네임 중복 확인 결과. 계정 정보는 반환하지 않는다.** (1 connections) — `src/backend/src/dait/schemas/nickname.py`
- **ambiguous_python_import_181c6df51641** (1 connections)
- **ambiguous_python_import_8ebbe343b706** (1 connections)
- **ambiguous_python_import_933b975faf4d** (1 connections)
- **ambiguous_python_import_95bf9722079b** (1 connections)
- **ambiguous_python_import_f01dbca9f9ed** (1 connections)

## Relationships

- [withdraw](withdraw.md) (5 shared connections)
- [backend/src/dait/services/auth_service.py](backend-src-dait-services-auth_service.py.md) (3 shared connections)
- [src/backend/src/dait/api/v1/auth_routes.py](src-backend-src-dait-api-v1-auth_routes.py.md) (3 shared connections)
- [backend/src/dait/services/account_service.py](backend-src-dait-services-account_service.py.md) (3 shared connections)
- [typing](typing.md) (3 shared connections)
- [3. 인증 API](3._인증_API.md) (2 shared connections)
- [ai_processor.py](ai_processor.py.md) (2 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [src/backend/src/dait/main.py](src-backend-src-dait-main.py.md) (1 shared connections)
- [backend/src/dait/schemas/auth.py](backend-src-dait-schemas-auth.py.md) (1 shared connections)
- [backend/src/dait/schemas/user.py](backend-src-dait-schemas-user.py.md) (1 shared connections)
- [DAIT_ui_v1.0.1/src/backend/src/dait/repositories/user_repository.py](DAIT_ui_v1.0.1-src-backend-src-dait-repositories-user_repository.py.md) (1 shared connections)

## Source Files

- `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- `src/backend/src/dait/api/v1/me_routes.py`
- `src/backend/src/dait/schemas/nickname.py`

## Audit Trail

- EXTRACTED: 47 (89%)
- INFERRED: 6 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*