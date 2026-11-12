# src/backend/src/dait/api/v1/interest_routes.py

> 21 nodes

## Key Concepts

- **replace_my_interests()** (10 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **src/backend/src/dait/api/v1/interest_routes.py** (10 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **my_interests()** (9 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **catalog()** (4 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **Depends** (2 connections)
- **get** (2 connections)
- **get_current_user** (2 connections)
- **get_settings** (2 connections)
- **MyInterestsResponse** (2 connections)
- **Settings** (2 connections)
- **UserRecord** (2 connections)
- **CatalogResponse** (1 connections)
- **InterestsUpdateRequest** (1 connections)
- **관심사 라우트. main에서 이 라우터 한 줄을 빼면 관심사 기능만 빠지고 나머지는 동작한다.** (1 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **선택 가능한 관심사 15개를 대주제별로 알려 준다(로그인 불필요). 입력: 없음 출력: CatalogResponse (대주제 3개, 각…** (1 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **내 관심사를 조회한다. 입력: settings, user (Bearer 토큰으로 확인된 본인) 출력: MyInterestsResponse…** (1 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **내 관심사를 보낸 목록으로 통째로 교체한다. 입력: body (코드 목록, 최대 15개, 빈 목록이면 선택 해제), settings, user…** (1 connections) — `src/backend/src/dait/api/v1/interest_routes.py`
- **ambiguous_python_import_0e5eb986cffa** (1 connections)
- **ambiguous_python_import_2955d9e1c057** (1 connections)
- **ambiguous_python_import_a1391bd664d8** (1 connections)
- **ambiguous_python_import_ecb5de50f5e1** (1 connections)

## Relationships

- [typing](typing.md) (2 shared connections)
- [DAIT_ui_v1.0.1/src/backend/src/dait/api/v1/settings_routes.py](DAIT_ui_v1.0.1-src-backend-src-dait-api-v1-settings_routes.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/interest_routes.py`

## Audit Trail

- EXTRACTED: 30 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*