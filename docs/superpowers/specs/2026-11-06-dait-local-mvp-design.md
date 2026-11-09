# DAIT 로컬 MVP 설계

## 의도

`docs/DAIT_v1.0.1_docs`의 화면·API·DB 설계를 실행 가능한 로컬 MVP로 옮긴다. 사용자는 별도 로그인 없이 고정된 로컬 데모 사용자로 메인 뉴스 목록, 뉴스 상세, 설정과 예약을 확인하고 변경할 수 있어야 한다.

## 목표

- 기존 `mockup/index.html`, `detail.html`, `settings.html`의 시각 구조를 제품 화면으로 재사용한다.
- 세 화면이 FastAPI의 `/v1` API와 실제로 통신하도록 한다.
- DB 설계서의 13개 테이블, 제약, 주요 인덱스를 로컬 SQLite에 생성한다.
- 앱 최초 실행 시 데모 사용자, 설정, 예약, 출처, 뉴스, 처리 결과와 관련 뉴스 샘플을 멱등하게 넣는다.
- 뉴스 목록·검색·정렬, 뉴스 상세, 설정 조회·저장, 예약 CRUD를 브라우저에서 동작시킨다.
- API 계약과 핵심 DB 제약을 자동 테스트로 검증한다.

## 비목표

- 회원가입·로그인·토큰·소셜 인증 화면과 실제 인증 흐름
- 외부 뉴스 사이트 수집, LLM 번역·요약, 메일 또는 인앱 알림 발송
- Redis 캐시·큐·분산 락, 백그라운드 스케줄 실행
- PostgreSQL/Supabase 배포와 Alembic 운영 마이그레이션
- React/Vite 도입 또는 기존 화면의 전면 재설계

## 피해야 할 결과

- 화면에 샘플 값을 하드코딩한 채 API 성공처럼 보이는 구현
- 설정·예약 변경이 새로고침 후 사라지는 구현
- DB 설계서와 다른 임의 테이블 구조 또는 FK가 비활성인 SQLite
- 데모 편의를 이유로 입력 검증, SQL 파라미터 바인딩, 접근성 기본 상태를 제거하는 구현
- 기존의 대규모 줄바꿈 변경이나 사용자 작업을 덮어쓰는 변경

## 제약

- Python FastAPI와 표준 라이브러리 `sqlite3`를 사용한다.
- 브라우저 코드는 기존 HTML/CSS와 바닐라 JavaScript를 사용한다.
- API prefix, 필드와 오류 형태는 `06_API_설계서_v1.0.1.md`를 따른다.
- 스키마와 데이터 관계는 `07_DB_설계서_v1.0.1.md`를 따른다.
- 모든 날짜·시각 API 값은 UTC ISO 8601 형식으로 반환하며 예약은 `Asia/Seoul`을 기본값으로 사용한다.
- 앱은 리포지토리 내부의 SQLite 파일 한 개를 사용하되, 테스트에서는 임시 DB 경로를 주입할 수 있어야 한다.
- 현재 작업 트리의 기존 변경은 보존하고 이번 구현 파일만 좁게 수정한다.

## 검토한 접근

### 1. 기존 목업 + 바닐라 JavaScript + FastAPI + `sqlite3` — 선택

현재 자산을 그대로 활용하고 새 의존성과 파일 수를 최소화한다. 로컬 MVP의 기능과 DB 계약을 구현하기에 충분하며 사용자가 승인했다.

### 2. FastAPI + SQLAlchemy

ORM 모델과 향후 PostgreSQL 전환에는 유리하지만, 현재 세 화면 MVP에는 모델·세션·마이그레이션 설정이 과하다.

### 3. React/Vite + FastAPI

대규모 프런트엔드 확장에는 적합하지만 기존 목업을 재작성하고 빌드 도구를 추가해야 하므로 이번 목표와 맞지 않는다.

## 구조

### 서버

FastAPI 앱 한 개가 다음을 담당한다.

- 앱 시작 시 SQLite 연결, `PRAGMA foreign_keys = ON`, 스키마 생성, 멱등 시드 실행
- `/v1` JSON API 제공
- `/`에서 메인, `/detail.html?id=...`에서 상세, `/settings.html`에서 설정 화면 제공
- 목업 CSS와 JavaScript 정적 파일 제공
- 예외를 공통 오류 응답(`code`, `message`, `request_id`, `fields`)으로 변환

라우터·서비스·저장소 계층은 현재 스캐폴드의 책임 구분을 따르되, 한 구현만 있는 추상 인터페이스나 불필요한 비동기 래퍼는 만들지 않는다. SQLite 연결과 쿼리는 작은 DB 모듈에 모으고 라우터는 검증된 요청을 해당 함수에 전달한다.

### 브라우저

- 메인: 시작 시 `GET /v1/news`; 검색, `rank/latest` 정렬, 초기화 시 query를 갱신; 카드에서 상세와 검증된 원문으로 이동
- 상세: URL의 `id`로 `GET /v1/news/{id}`; 요약·번역·처리·원본·관련 뉴스 렌더링; 원문 새 탭과 링크 복사 상태 제공
- 설정: `GET /v1/me/settings`와 `GET /v1/me/schedules`; 저장 시 `PATCH /v1/me/settings`; 예약 생성·수정·삭제 API 호출
- 세 화면 모두 로딩, 빈 결과, API 오류를 텍스트 상태로 제공하고 동적 메시지는 `aria-live`로 알린다.

## 로컬 데모 사용자

- ID: `usr_demo_local`
- 이메일: `demo@dait.local`
- 상태: `ACTIVE`
- 실제 로그인 API와 비밀번호는 제공하지 않는다.
- `/v1/me/*` 요청은 서버 내부에서 항상 이 사용자 ID로 범위를 제한한다.
- 이 동작은 로컬 MVP 전용임을 README와 코드 상수에 명시한다.

## API 범위

### 구현

- `GET /healthz`
- `GET /readyz` — SQLite 연결 상태만 확인하고 Redis는 사용하지 않는다고 표시
- `GET /v1/news`
  - `category=AI`, 선택적 `q`, `sort=rank|latest`, `page_size=1..50`
  - 제목과 `summary_lines`의 대소문자 비구분 부분 검색
  - `READY`와 `INSUFFICIENT` 기사를 노출하며 `INSUFFICIENT`는 부분 처리 상태와 가능한 콘텐츠를 명시한다. `PENDING`과 `FAILED`는 목록에서 제외한다.
  - `rank` 정렬은 처리 완성도(`READY` 우선) → 출처 `priority` 오름차순 → `published_at` 내림차순 → 뉴스 ID 오름차순으로 결정한다. 별도 품질 점수가 생기기 전까지 이 규칙을 로컬 MVP의 랭킹 기준으로 사용한다.
  - 이번 시드 규모에서는 `next_cursor=null`, `has_more=false`; cursor가 전달되면 명시적으로 검증 오류를 반환하거나 단순 offset cursor를 구현하는 선택은 구현 계획에서 결정한다.
- `GET /v1/news/{news_id}`
- `GET /v1/me/settings`
- `PATCH /v1/me/settings`
- `GET /v1/me/schedules`
- `POST /v1/me/schedules`
- `PATCH /v1/me/schedules/{schedule_id}`
- `DELETE /v1/me/schedules/{schedule_id}`

### 제외

- `/v1/auth/*`
- `DELETE /v1/me`

제외 API는 인증·개인정보 삭제 정책이 필요한 별도 기능이므로 화면의 계정·정책 버튼은 안내용 비활성 상태로 둔다.

## SQLite 설계

DB 설계서의 아래 13개 테이블을 생성한다.

1. `users`
2. `auth_identities`
3. `refresh_sessions`
4. `user_settings`
5. `schedules`
6. `sources`
7. `news`
8. `content_results`
9. `news_relations`
10. `jobs`
11. `job_attempts`
12. `notification_deliveries`
13. `audit_logs`

SQLite 매핑은 문자열 ID와 UTC 시각을 `TEXT`, boolean을 `INTEGER CHECK (... IN (0,1))`, JSON 배열·객체를 유효한 JSON `TEXT`, 점수를 `REAL`로 저장한다. `default_count IN (5,10)`, 자기 자신 관련 뉴스 금지, 문서의 UNIQUE/FK와 상태·조회용 인덱스를 적용한다. 삭제 정책은 사용자 소유 데이터에 필요한 `ON DELETE CASCADE`, 공유 뉴스 관계에 필요한 문서 의미를 구현 계획에서 명시한다.

시드는 최소 3개의 뉴스로 구성한다. READY 기사 2건과 부분/내용 부족 상태 기사 1건을 두고, 각 기사에 출처·3줄 요약·번역·관련 뉴스가 연결되도록 한다. 재실행 시 중복되지 않도록 고정 불투명 ID와 `INSERT OR IGNORE`/upsert를 사용한다.

## 입력 검증과 오류

- FastAPI/Pydantic 모델에서 추가 필드를 거부한다.
- 검색어는 trim 후 최대 100자, `page_size`는 1~50, category는 `AI`, sort는 `rank/latest`만 허용한다.
- 설정의 기본 개수는 5 또는 10이며 키워드는 trim·중복 제거·길이 제한을 적용한다.
- `source_ids`는 활성 승인 출처만 허용한다.
- 예약 시각은 `HH:mm`, 시간대는 이번 MVP에서 `Asia/Seoul`, 카테고리는 `AI`만 허용한다.
- 모든 SQL은 파라미터 바인딩을 사용한다.
- 없는 뉴스와 다른 사용자의 예약은 정보가 드러나지 않는 404를 반환한다.

## 테스트와 완료 기준

- 임시 SQLite DB로 스키마 13개 테이블, FK 활성화, 주요 CHECK/UNIQUE 제약을 확인한다.
- 앱 시작을 두 번 실행해 시드가 중복되지 않음을 확인한다.
- 뉴스 목록 기본 순서, 최신순, 제목/요약 검색, 빈 결과, 잘못된 query를 확인한다.
- 목록에서 `READY`가 `INSUFFICIENT`보다 먼저 오고 `PENDING`/`FAILED`가 제외되는지 확인한다.
- 뉴스 상세 정상/404와 관련 뉴스 매핑을 확인한다.
- 설정 조회 → PATCH → 재조회 영속성을 확인한다.
- 예약 생성 → 수정 → 조회 → 삭제와 데모 사용자 범위를 확인한다.
- 정적 화면 세 개와 CSS/JS가 HTTP 200으로 제공되는지 확인한다.
- 전체 자동 테스트 명령과 수동 실행 명령을 README에 기록한다.

완료란 로컬 서버 한 개를 실행해 세 화면을 탐색할 수 있고, 화면 변경이 API를 통해 SQLite에 반영되며, 자동 테스트가 통과하는 상태다.

## 구현자에게 남기는 결정

- 현재 환경에 설치된 FastAPI/Pydantic 버전에 맞춘 최소 패키지 선언 형식
- 기존 스캐폴드 파일 중 실제로 필요한 최소 파일 배치
- cursor를 지원할지, 미지원 입력을 422로 명확히 제한할지
- 상세 읽기 시간의 간단한 계산 방식
- 화면 목업을 `src/frontend`로 복사할지, 기존 문서 목업을 정적 루트로 참조할지 여부. 단, 문서 원본을 실행 중 변경하는 구조는 피한다.
