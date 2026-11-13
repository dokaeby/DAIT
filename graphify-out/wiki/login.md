# login

> 26 nodes

## Key Concepts

- **login()** (13 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **signup()** (11 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **logout()** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **refresh()** (7 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **_attach_interests()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **post** (4 connections)
- **Request** (4 connections)
- **SettingsDep** (4 connections)
- **AuthResponse** (3 connections)
- **Depends** (3 connections)
- **UserRecord** (3 connections)
- **get_optional_user** (2 connections)
- **get_current_user** (1 connections)
- **get_throttles** (1 connections)
- **LoginRequest** (1 connections)
- **LoginThrottles** (1 connections)
- **RefreshRequest** (1 connections)
- **ResultResponse** (1 connections)
- **Settings** (1 connections)
- **SignupRequest** (1 connections)
- **TokenPair** (1 connections)
- **응답에 DB에 저장된 관심사 목록을 붙인다. 입력: response (서비스가 만든 가입·로그인 응답), settings (앱 설정) 출력:…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **이메일·비밀번호로 가입하고 로그인 토큰을 받는다. 입력: body (이메일, 비밀번호 8~128자, 비밀번호 확인, 약관 동의),…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **이메일·비밀번호로 로그인하고 토큰을 받는다. 입력: body (이메일, 비밀번호), request, settings, throttles,…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- **refresh 토큰으로 새 access·refresh 토큰을 받는다(로그인 유지). 입력: body (refresh 토큰), request,…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`
- *... and 1 more nodes in this community*

## Relationships

- [api/auth.py](api-auth.py.md) (5 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/auth.py`

## Audit Trail

- EXTRACTED: 44 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*