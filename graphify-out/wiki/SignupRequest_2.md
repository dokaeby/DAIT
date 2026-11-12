# SignupRequest

> 12 nodes

## Key Concepts

- **SignupRequest** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **._check_confirm_and_terms()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **._no_duplicate_interests()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **._check_email_length()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **field_validator** (2 connections)
- **InterestCode** (1 connections)
- **model_validator** (1 connections)
- **Self** (1 connections)
- **회원가입 요청. 알 수 없는 필드는 거부한다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **가입 시 보낸 관심사에 중복이 없는지 확인한다. 입력: value (관심사 코드 목록) 출력: 같은 목록 기능: 중복이면 ValueError…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **이메일이 254자를 넘지 않는지 확인한다. 입력: value (형식 검증을 통과한 이메일) 출력: 같은 이메일 기능: 254자를 넘으면…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`
- **비밀번호 확인 일치와 약관 동의를 확인한다. 입력: 없음(이미 검증된 필드들) 출력: self 기능: 두 비밀번호가 다르거나 약관 미동의면…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`

## Relationships

- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-schemas-auth.py.md) (2 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py`

## Audit Trail

- EXTRACTED: 14 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*