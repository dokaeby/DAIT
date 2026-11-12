# src/backend/src/dait/repositories/user_repository.py

> 25 nodes

## Key Concepts

- **src/backend/src/dait/repositories/user_repository.py** (13 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **DbConnection** (6 connections)
- **find_by_email()** (5 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **find_by_id()** (5 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **_to_record()** (5 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **insert_user()** (4 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **UserRecord** (4 connections)
- **DuplicateEmailError** (3 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **DuplicateNicknameError** (3 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **delete_user()** (3 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **nickname_exists()** (3 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **update_nickname()** (3 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **Exception** (2 connections)
- **users 테이블 접근. SQL은 파라미터 바인딩(?)만 쓰고 문자열을 이어 붙이지 않는다.** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **이미 같은 이메일의 사용자가 있을 때(유니크 제약 위반).** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **id로 사용자를 찾는다. 입력: conn (열려 있는 연결), user_id (토큰에서 꺼낸 사용자 id) 출력: UserRecord 또는…** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **사용자를 실제로 삭제한다. 입력: conn (열려 있는 트랜잭션 연결), user_id (삭제할 사용자 id) 출력: bool (지웠으면…** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **중복 확인 이후 동시에 같은 닉네임으로 가입한 경우도 차단한다.** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **정규화된 닉네임을 대소문자 구분 없이 비교한다.** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **닉네임과 비교 키를 함께 갱신하고 유니크 제약으로 중복을 차단한다.** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **사용자 한 명을 저장한다. 입력: conn (열려 있는 트랜잭션 연결), user (저장할 사용자 레코드) 출력: 없음 기능: 이메일 유니크…** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **DB 행을 사용자 레코드로 바꾼다. 입력: row (users 테이블의 컬럼 순서대로 읽은 행) 출력: UserRecord (검증된 모델)…** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **이메일로 사용자를 찾는다. 입력: conn (열려 있는 연결), email (소문자로 맞춘 이메일) 출력: UserRecord 또는 None…** (1 connections) — `src/backend/src/dait/repositories/user_repository.py`
- **ambiguous_python_import_2632039ef0e6** (1 connections)
- **ambiguous_python_import_8e0191bfcd9d** (1 connections)

## Relationships

- [datetime](datetime.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/user_repository.py`

## Audit Trail

- EXTRACTED: 36 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*