# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py

> 17 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **Connection** (5 connections)
- **find_by_hash()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **insert_refresh_token()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **revoke_all_for_user()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **revoke_family()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **revoke_if_active()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **datetime** (4 connections)
- **RefreshTokenRecord** (1 connections)
- **StoredRefreshToken** (1 connections)
- **refresh_tokens 테이블 접근. 토큰 원문은 받지도 저장하지도 않는다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **refresh 토큰 해시 한 건을 저장한다. 입력: conn (열려 있는 트랜잭션 연결), record (해시와 만료 시각을 담은 레코드)…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **토큰 해시로 저장된 refresh 토큰을 찾는다. 입력: conn (열려 있는 연결), token_hash (요청으로 받은 토큰의…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **아직 폐기되지 않은 토큰 하나를 폐기한다. 입력: conn (열려 있는 트랜잭션 연결), token_id (토큰 행 id), now (UTC…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **같은 로그인 계열(family)의 살아 있는 토큰을 모두 폐기한다. 입력: conn (열려 있는 트랜잭션 연결), family_id (계열…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **한 사용자의 살아 있는 refresh 토큰을 모두 폐기한다. 입력: conn (열려 있는 트랜잭션 연결), user_id (사용자 id),…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`
- **ambiguous_python_import_bffab0423029** (1 connections)

## Relationships

- [datetime](datetime.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/repositories/token_repository.py`

## Audit Trail

- EXTRACTED: 24 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*