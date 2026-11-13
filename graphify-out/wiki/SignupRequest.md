# SignupRequest

> 14 nodes

## Key Concepts

- **SignupRequest** (7 connections) — `src/backend/src/dait/schemas/auth.py`
- **._check_password_confirmation()** (4 connections) — `src/backend/src/dait/schemas/auth.py`
- **._no_duplicate_interests()** (4 connections) — `src/backend/src/dait/schemas/auth.py`
- **._check_email_length()** (3 connections) — `src/backend/src/dait/schemas/auth.py`
- **._empty_nickname()** (3 connections) — `src/backend/src/dait/schemas/auth.py`
- **field_validator** (3 connections)
- **InterestCode** (1 connections)
- **model_validator** (1 connections)
- **Self** (1 connections)
- **회원가입 요청. 알 수 없는 필드는 거부한다.** (1 connections) — `src/backend/src/dait/schemas/auth.py`
- **빈 선택 입력은 이메일 표시를 뜻한다.** (1 connections) — `src/backend/src/dait/schemas/auth.py`
- **가입 시 보낸 관심사에 중복이 없는지 확인한다. 입력: value (관심사 코드 목록) 출력: 같은 목록 기능: 중복이면 ValueError…** (1 connections) — `src/backend/src/dait/schemas/auth.py`
- **이메일이 254자를 넘지 않는지 확인한다. 입력: value (형식 검증을 통과한 이메일) 출력: 같은 이메일 기능: 254자를 넘으면…** (1 connections) — `src/backend/src/dait/schemas/auth.py`
- **비밀번호 확인이 일치하는지 검사한다. 입력: 없음(이미 검증된 필드들) 출력: self 기능: 두 비밀번호가 다르면 ValueError.…** (1 connections) — `src/backend/src/dait/schemas/auth.py`

## Relationships

- [backend/src/dait/schemas/auth.py](backend-src-dait-schemas-auth.py.md) (2 shared connections)

## Source Files

- `src/backend/src/dait/schemas/auth.py`

## Audit Trail

- EXTRACTED: 17 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*