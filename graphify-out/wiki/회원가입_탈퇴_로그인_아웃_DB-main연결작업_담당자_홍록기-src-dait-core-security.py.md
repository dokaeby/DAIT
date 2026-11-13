# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py

> 20 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py** (17 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **AccessClaims** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **create_access_token()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **decode_access_token()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **hash_password()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **hash_refresh_token()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **new_refresh_token()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **verify_password()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **datetime** (2 connections)
- **argon2_exceptions** (2 connections)
- **BaseModel** (1 connections)
- **비밀번호 해시와 토큰(JWT access, 랜덤 refresh) 도구. DB·HTTP를 모르는 순수 함수만 둔다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **refresh 토큰 원문의 저장용 해시를 만든다. 입력: token (refresh 토큰 원문) 출력: str (SHA-256 16진 문자열…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **access 토큰 안에 들어 있는 값.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **비밀번호를 argon2id 해시로 바꾼다. 입력: raw (사용자가 입력한 평문 비밀번호) 출력: str (argon2id 해시 문자열, 솔트…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **평문 비밀번호가 해시와 맞는지 확인한다. 입력: raw (입력된 평문), password_hash (저장된 해시, 사용자가 없으면 None)…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **짧은 수명의 access JWT를 만든다. 입력: user_id (사용자 id), secret (서명 키), minutes (유효 분),…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **access JWT의 서명과 만료를 검증하고 값을 꺼낸다. 입력: token (클라이언트가 보낸 JWT), secret (서명 키) 출력:…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **추측할 수 없는 refresh 토큰 원문을 만든다. 입력: 없음 출력: str (URL에 안전한 무작위 문자열, 256비트) 기능:…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`
- **ambiguous_python_import_879fc183dc02** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [backend/src/dait/core/security.py](backend-src-dait-core-security.py.md) (2 shared connections)
- [ui/conftest.py](ui-conftest.py.md) (1 shared connections)
- [backend/tests/support.py](backend-tests-support.py.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py`

## Audit Trail

- EXTRACTED: 28 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*