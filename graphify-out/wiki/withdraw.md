# withdraw

> 20 nodes

## Key Concepts

- **withdraw()** (13 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **session()** (11 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **change_nickname()** (9 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **Depends** (3 connections)
- **get_settings** (3 connections)
- **Settings** (3 connections)
- **UserRecord** (3 connections)
- **get_current_user** (2 connections)
- **delete** (1 connections)
- **get** (1 connections)
- **get_optional_user** (1 connections)
- **get_throttles** (1 connections)
- **LoginThrottles** (1 connections)
- **patch** (1 connections)
- **Request** (1 connections)
- **ResultResponse** (1 connections)
- **SessionResponse** (1 connections)
- **WithdrawRequest** (1 connections)
- **로그인 상태를 알려 준다(화면의 메뉴 노출 판단용). 입력: settings (앱 설정), user (유효한 Bearer 토큰이 있으면 본인,…** (1 connections) — `src/backend/src/dait/api/v1/me_routes.py`
- **회원탈퇴: 비밀번호를 다시 확인하고 계정과 토큰을 실제로 삭제한다. 입력: body (재입력한 비밀번호), request, settings,…** (1 connections) — `src/backend/src/dait/api/v1/me_routes.py`

## Relationships

- [me_routes.py](me_routes.py.md) (5 shared connections)
- [StoredNews](StoredNews.md) (2 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/me_routes.py`

## Audit Trail

- EXTRACTED: 29 (88%)
- INFERRED: 4 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*