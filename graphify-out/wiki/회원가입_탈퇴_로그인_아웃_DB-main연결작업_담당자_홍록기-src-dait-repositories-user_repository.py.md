# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py

> 18 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py** (10 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **find_by_email()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **find_by_id()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **_to_record()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **insert_user()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **Connection** (4 connections)
- **UserRecord** (4 connections)
- **DuplicateEmailError** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **delete_user()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **Exception** (1 connections)
- **users 테이블 접근. SQL은 파라미터 바인딩(?)만 쓰고 문자열을 이어 붙이지 않는다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **이미 같은 이메일의 사용자가 있을 때(유니크 제약 위반).** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **사용자 한 명을 저장한다. 입력: conn (열려 있는 트랜잭션 연결), user (저장할 사용자 레코드) 출력: 없음 기능: 이메일 유니크…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **DB 행을 사용자 레코드로 바꾼다. 입력: row (users 테이블의 컬럼 순서대로 읽은 행) 출력: UserRecord (검증된 모델)…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **이메일로 사용자를 찾는다. 입력: conn (열려 있는 연결), email (소문자로 맞춘 이메일) 출력: UserRecord 또는 None…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **id로 사용자를 찾는다. 입력: conn (열려 있는 연결), user_id (토큰에서 꺼낸 사용자 id) 출력: UserRecord 또는…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **사용자를 실제로 삭제한다. 입력: conn (열려 있는 트랜잭션 연결), user_id (삭제할 사용자 id) 출력: bool (지웠으면…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`
- **ambiguous_python_import_f423db33544a** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/user_repository.py`

## Audit Trail

- EXTRACTED: 27 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*