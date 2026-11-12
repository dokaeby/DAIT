# backend/src/dait/services/auth_service.py

> 43 nodes

## Key Concepts

- **backend/src/dait/services/auth_service.py** (28 connections) — `src/backend/src/dait/services/auth_service.py`
- **_issue_tokens()** (10 connections) — `src/backend/src/dait/services/auth_service.py`
- **login()** (10 connections) — `src/backend/src/dait/services/auth_service.py`
- **_rotate()** (9 connections) — `src/backend/src/dait/services/auth_service.py`
- **signup()** (9 connections) — `src/backend/src/dait/services/auth_service.py`
- **datetime** (8 connections)
- **refresh()** (7 connections) — `src/backend/src/dait/services/auth_service.py`
- **_to_response()** (7 connections) — `src/backend/src/dait/services/auth_service.py`
- **Settings** (7 connections)
- **logout()** (5 connections) — `src/backend/src/dait/services/auth_service.py`
- **_revoke_family_for_reuse()** (5 connections) — `src/backend/src/dait/services/auth_service.py`
- **check_nickname()** (4 connections) — `src/backend/src/dait/services/auth_service.py`
- **TokenPair** (4 connections)
- **AuthResponse** (3 connections)
- **DbConnection** (3 connections)
- **UserRecord** (3 connections)
- **LoginRequest** (1 connections)
- **LoginThrottles** (1 connections)
- **RefreshRequest** (1 connections)
- **SignupRequest** (1 connections)
- **가입·로그인·토큰 갱신·로그아웃 규칙을 처리한다. HTTP 형식은 api, SQL은 repositories가 맡는다.** (1 connections) — `src/backend/src/dait/services/auth_service.py`
- **회원가입을 처리하고 최초 토큰을 발급한다. 입력: settings (앱 설정), request (검증된 가입 요청), client_ip (감사…** (1 connections) — `src/backend/src/dait/services/auth_service.py`
- **중복 확인은 안내이며 가입 시 DB 유니크 인덱스로 다시 보장한다.** (1 connections) — `src/backend/src/dait/services/auth_service.py`
- **로그인을 처리하고 새 토큰을 발급한다. 입력: settings (앱 설정), request (검증된 로그인 요청), throttles (잠금…** (1 connections) — `src/backend/src/dait/services/auth_service.py`
- **폐기된 토큰이 다시 쓰였을 때 그 계열 전체를 폐기한다. 입력: conn (열려 있는 트랜잭션 연결), user_id (소유자),…** (1 connections) — `src/backend/src/dait/services/auth_service.py`
- *... and 18 more nodes in this community*

## Relationships

- [me_routes.py](me_routes.py.md) (3 shared connections)
- [onboarding_repository.py](onboarding_repository.py.md) (3 shared connections)
- [datetime](datetime.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/services/auth_service.py`

## Audit Trail

- EXTRACTED: 78 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*