# KAN-10 설정 · 카테고리 표시 순서 · 선호 검색어 · 예약 알림

기준일: 2026-11-10 / Asia/Seoul

## 기능 요약

| 기능 | 위치 | 동작 |
|---|---|---|
| 설정 저장 | `/settings` | 화면의 값을 `PUT /api/settings`로 계정별 저장. 새로고침·재로그인 후에도 복원 |
| 카테고리 표시·순서 | 설정 > 검색·관심 설정 | ↑↓로 순서, 스위치로 숨김. 메인 카테고리 칩에 적용 |
| 선호 검색어 | 설정 > 검색·관심 설정, 메인 검색창 아래 | 최대 3개, 공백 정리·중복 제거. 메인 칩을 누르면 바로 검색 |
| 예약 알림 | 설정 > 예약 알림 | 요일·시각(KST)·받을 기사(관심 카테고리/선호 검색어)·최대 건수. 서버가 30초마다 확인해 정시에 1회 실행 |
| 예약 소식함 | 왼쪽 메뉴 `🔔 예약 소식함`, `/inbox` | 예약 소식 최근 30개 보관. 인앱 알림이 켜져 있으면 "새 N" 표시, 열면 읽음 처리 |
| 노출 수 | 설정 > 노출·알림 | 메인 목록 기사 수(10/5) |

메일 알림 스위치는 값만 저장하며 실제 발송은 이메일 등록·인증 단계에서 연결합니다.

## 저장 위치

`data/users.db`에 아래 테이블을 자동 생성합니다(기존 테이블은 변경하지 않음).

- `user_settings(owner_key, settings_json, saved_at, last_run_at)`
- `digests`, `digest_items` (예약 소식함)

`last_run_at`으로 같은 예약 시각이 두 번 실행되지 않게 막고, 저장 시각 이전에 이미 지난 예약은 실행하지 않습니다.

## 파일과 계층

| 계층 | 파일 |
|---|---|
| schemas | `dait/schemas.py` (`UserSettings`, `ScheduleSettings`, `Digest` 등 추가) |
| repositories | `dait/repositories/settings_repository.py` (SQL은 여기에만) |
| services | `dait/services/settings_service.py`, `dait/services/schedule_worker.py` |
| api | `dait/api/v1/settings_routes.py` (`/settings`, `/api/settings`, `/inbox`, `/api/inbox*`) |
| 화면 | `frontend/views.py`, `assets/settings.js`, `assets/app.js`(칩 클릭), `assets/app.css` |

## 테스트 실행

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/unit/services/test_settings.py -q   # 단위 27개
.\.venv\Scripts\python.exe -m playwright install chromium                     # 최초 1회
.\.venv\Scripts\python.exe -m pytest tests/ui -q                               # UI 자동화 11개
```

UI 테스트는 임시 폴더(`DAIT_PROJECT_ROOT`)에 고정 기사 4건과 빈 회원 DB를 만들고 서버를 띄워 실행하므로 실제 `data/`를 건드리지 않습니다.

| UI 케이스 | 내용 |
|---|---|
| UI-AUTH-001 | 비로그인 `/settings` 접근 시 메인으로 이동 |
| UI-SET-001 | 화면 값과 `GET /api/settings` 일치 |
| UI-SET-002 | 예약 09:00 저장 시 PUT 1회, 다음 예약 표시 갱신 |
| UI-SET-003 | 예약 끄기 저장 후 새로고침해도 꺼짐 |
| UI-SET-005 | 검색어 공백·중복 정리 후 저장·복원 |
| UI-SET-007 | 4번째 검색어 오류 표시, 저장 요청 없음 |
| UI-SET-009 | 새 페이지에서 저장값 복원 |
| UI-STATE-004 | 저장 버튼 더블클릭 시 요청 1회 |
| KAN-10 | 카테고리 순서·숨김의 메인 반영, 선호 검색어 칩 검색, 지금 받아보기→소식함·배지 |
