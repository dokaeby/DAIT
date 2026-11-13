# src/backend/src/dait/repositories/settings_repository.py

> 17 nodes

## Key Concepts

- **src/backend/src/dait/repositories/settings_repository.py** (11 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **SettingsRow** (8 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **get_row()** (5 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **save_row()** (4 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **_to_row()** (4 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **dumps_list()** (2 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **loads_list()** (2 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **DbConnection** (2 connections)
- **NamedTuple** (1 connections)
- **user_settings 테이블 접근. 사용자당 1행이며 항상 user_id로 범위를 제한한다.** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **문자열 목록을 JSON TEXT로 직렬화한다. 입력: values (코드·키워드·출처 ID 목록) 출력: str (JSON 배열 문자열)…** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **user_settings 한 행. JSON 컬럼은 TEXT 원문 그대로 둔다.** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **JSON TEXT를 문자열 목록으로 되돌린다. 입력: raw (저장된 TEXT, None 가능) 출력: str 목록 (파싱 실패·비목록이면 빈…** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **DB 행을 SettingsRow로 바꾼다. 입력: row (컬럼 순서대로 읽은 행) 출력: SettingsRow 기능: 시각 문자열을…** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **사용자의 설정 행을 읽는다. 입력: conn (연결), user_id (인증된 본인 id) 출력: SettingsRow 또는 None (아직…** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **설정 행을 만들거나 통째로 갱신한다. 입력: conn (트랜잭션 연결), row (저장할 전체 값) 출력: 없음 기능: user_id 충돌 시…** (1 connections) — `src/backend/src/dait/repositories/settings_repository.py`
- **ambiguous_python_import_293f24baaa8f** (1 connections)

## Relationships

- [NewsCategory](NewsCategory.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [typing](typing.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/settings_repository.py`

## Audit Trail

- EXTRACTED: 26 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*