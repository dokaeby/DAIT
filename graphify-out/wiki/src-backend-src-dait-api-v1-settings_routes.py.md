# src/backend/src/dait/api/v1/settings_routes.py

> 21 nodes

## Key Concepts

- **src/backend/src/dait/api/v1/settings_routes.py** (22 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **update_my_schedule()** (8 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **delete_my_schedule()** (7 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **update_my_settings()** (7 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **get_my_settings()** (6 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **list_my_schedules()** (6 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **CurrentUser** (6 connections)
- **SettingsDep** (6 connections)
- **get** (2 connections)
- **patch** (2 connections)
- **delete** (1 connections)
- **Response** (1 connections)
- **FR-SET-01~03 설정 API: /v1/me/settings 와 /v1/me/schedules. 모든 경로는 인증 필수이며 사용자 ID는…** (1 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **본인의 예약을 삭제하고 감사 로그를 남긴다. 입력: schedule_id (경로), settings, user 출력: 204 (본문 없음)…** (1 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **관심 키워드·승인 출처·카테고리·노출 수·알림 설정을 조회한다. 입력: settings, user (Bearer 토큰으로 확인된 본인) 출력:…** (1 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **설정을 부분 수정하고 서버가 정규화한 저장 값을 돌려준다. 입력: body (보낸 필드만 변경), settings, user (본인) 출력:…** (1 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **본인의 예약을 부분 수정하고 변경된 전체 객체를 돌려준다. 입력: schedule_id (경로), body (보낸 필드만 변경),…** (1 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **ambiguous_python_import_0d8cb2cdd97e** (1 connections)
- **ambiguous_python_import_15afbadd46fd** (1 connections)
- **ambiguous_python_import_175248632c0a** (1 connections)
- **ambiguous_python_import_ac1552eb6af3** (1 connections)

## Relationships

- [schedule_service.py](schedule_service.py.md) (10 shared connections)
- [NewsCategory](NewsCategory.md) (10 shared connections)
- [typing](typing.md) (2 shared connections)
- [datetime](datetime.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/settings_routes.py`

## Audit Trail

- EXTRACTED: 47 (89%)
- INFERRED: 6 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*