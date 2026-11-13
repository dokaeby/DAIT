# withdraw

> 18 nodes

## Key Concepts

- **withdraw()** (13 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/me.py`
- **session()** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/me.py`
- **Depends** (2 connections)
- **get_settings** (2 connections)
- **Settings** (2 connections)
- **UserRecord** (2 connections)
- **delete** (1 connections)
- **get** (1 connections)
- **get_current_user** (1 connections)
- **get_optional_user** (1 connections)
- **get_throttles** (1 connections)
- **LoginThrottles** (1 connections)
- **Request** (1 connections)
- **ResultResponse** (1 connections)
- **SessionResponse** (1 connections)
- **WithdrawRequest** (1 connections)
- **로그인 상태를 알려 준다(화면의 메뉴 노출 판단용). 입력: settings (앱 설정), user (유효한 Bearer 토큰이 있으면 본인,…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/me.py`
- **회원탈퇴: 비밀번호를 다시 확인하고 계정과 토큰을 실제로 삭제한다. 입력: body (재입력한 비밀번호), request, settings,…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/me.py`

## Relationships

- [me.py](me.py.md) (2 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/me.py`

## Audit Trail

- EXTRACTED: 22 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*