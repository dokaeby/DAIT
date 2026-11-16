# DAIT API 설계서 v1.0.5

| 항목 | 기준 |
|---|---|
| 검토일 | 2026-11-16 (Asia/Seoul) |
| 구현 기준 | src/backend/src/dait의 현재 라우트·Pydantic 모델·서비스·오류 처리 |
| 서비스 목적 | 뉴스 수집 결과·AI 요약 조회, 계정·관심사·예약 관리 |
| 운영 Base URL | https://dait.onrender.com/v1 (배포 주소, 이번 작업에서 배포 상태를 검증하지 않음) |
| 로컬 Base URL | http://localhost:8000/v1 (기본 개발 실행 예시, 포트 변경 가능) |
| 상태 확인 경로 | /healthz, /readyz는 /v1 바깥 |
| 데이터·버전 | JSON / UTF-8 / API v1 |
| 인증 | Authorization: Bearer <access_token>; 내부 tick은 별도 비밀값 |
| 가이드 | [교과목 프로젝트 가이드](https://playdatacademy.notion.site/AI-4-3e4d943bcac28072a65ad03b00ab9f8a) 산출물 1; 화면 연결은 산출물 2 대응 |

## 1. 범위와 실제 구현 차이

기존 v1.0.5 문구보다 현재 실행 코드가 우선한다. 문서만 수정했으며 서비스 코드는 변경하지 않았다.

- 현재 `language=ko|en` 파라미터, 응답의 `original_language`·번역 관련 필드 및 `en.*` 관심사 코드가 구현에 존재한다. 한국어 15개만 제공한다고 단정하지 않는다. 관심사 스키마 상한은 30개이다.
- 예약 서비스의 생성 상한은 사용자당 5개이다. `ScheduleListResponse`의 스키마 상한 10은 응답 검증 한도이며 생성 허용 개수가 아니다.
- Google 로그인은 구현됐으며 환경설정에 따라 활성화된다. 이메일 인증의 Bearer 토큰과 OAuth state용 쿠키를 구분한다.
- 메인 화면은 검색·국내/관심사 칩·기사 카드가 기준이다. `sort` API 옵션이 존재하는 것과 화면에 정렬 선택기가 있는 것은 별개다. 내부 상세 화면은 미제공이며 원문 새 탭과 복사를 사용한다.
- 설정의 `default_count`·알림 API 필드는 유지되지만 화면의 목록 표시·노출/알림 메뉴는 미제공이다.
- 검증 범위는 소스 계약·모델 예시 검증이다. 운영 API의 실응답이나 배포 DB에 연결하지 않았다.


## 2. 공통 계약과 오류

날짜·시각은 timezone-aware ISO 8601, 저장·교환 기준은 UTC이다. 화면은 Asia/Seoul로 변환한다. 외부 ID는 불투명 문자열이다. HTTPS 원문 URL은 모델 검증을 거친다. 페이지네이션은 cursor 기반이다. 요청 모델은 알 수 없는 필드를 거부하며 Google 공급자 응답 모델은 필요한 필드만 읽기 위해 `extra="ignore"` 예외를 둔다. 요청 본문 미제공과 nullable은 별개다.

### 2.1 실제 표준 오류 응답

```json
{
  "code": "VALIDATION_ERROR",
  "message": "요청 형식이 올바르지 않습니다.",
  "request_id": "req-example-001"
}
```
| 필드 | 타입 | 필수 | 상세 |
|---|---|---|---|
| code | string, 1~64자 | Y | 기계 판독 오류 코드 |
| message | string, 1~200자 | Y | 외부 공개 가능한 안내 |
| request_id | string, 1~64자 | Y | 응답 X-Request-ID와 연계, 서버 로그 추적 |

**상세 정보 제공 범위:** 현 구현은 오류 본문의 `fields`·`details`를 반환하지 않는다. 필드별 원인·발생 조건은 아래 API 정의와 모델 제약 표로 문서화한다. 가이드 예시의 구조화된 `details` 응답 필드를 그대로 충족하는 구현은 아니며, 이를 실제 응답처럼 추가 기재하지 않는다. 비밀번호·토큰·SQL·스택·사용자 입력 원문은 공개하지 않는다.

### 2.2 구현 오류 코드
| HTTP | 코드 | 공개 메시지 |
|---|---|---|
| 500 | INTERNAL_ERROR | 서버 내부 오류가 발생했습니다. |
| 503 | NOT_READY | 서비스가 아직 준비되지 않았습니다. |
| 409 | EMAIL_ALREADY_REGISTERED | 이미 가입된 이메일입니다. |
| 422 | WEAK_PASSWORD | 너무 흔한 비밀번호입니다. 다른 비밀번호를 사용해 주세요. |
| 409 | NICKNAME_TAKEN | 이미 사용 중인 닉네임입니다. 다른 닉네임을 입력해 주세요. |
| 401 | INVALID_CREDENTIALS | 이메일 또는 비밀번호가 올바르지 않습니다. |
| 429 | TOO_MANY_ATTEMPTS | 로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요. |
| 409 | ALREADY_LOGGED_IN | 이미 로그인되어 있습니다. |
| 422 | VALIDATION_ERROR | 입력값을 확인해 주세요. |
| 404 | NEWS_NOT_FOUND | 요청한 뉴스를 찾을 수 없습니다. |
| 404 | SCHEDULE_NOT_FOUND | 요청한 예약을 찾을 수 없습니다. |
| 401 | AUTHENTICATION_FAILED | 인증에 실패했습니다. |
| 502 | CRON_JOB_ORG_UNAVAILABLE | 예약 실행 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요. |
| 401 | INVALID_TOKEN | 인증 정보가 올바르지 않습니다. |
| 404 | SOCIAL_LOGIN_DISABLED | 사용할 수 없는 기능입니다. |
| 403 | RECENT_LOGIN_REQUIRED | 보안을 위해 다시 로그인한 뒤 확인 문구를 입력해 주세요. |

### 2.3 4xx·5xx 처리 규칙
| 상태 | 발생 조건 | 호출자 처리 |
|---|---|---|
| 400 BAD_REQUEST | Content-Length가 숫자가 아님 | 헤더 형식 수정, 같은 요청 자동 재시도 금지 |
| 401 | 토큰·자격·tick 비밀값 실패 | 토큰 갱신 또는 재로그인; 자격 입력 재확인 |
| 403 RECENT_LOGIN_REQUIRED | Google 전용 계정 탈퇴 확인 미충족 | 5분 이내 재로그인 후 확인 문구 입력 |
| 404 | 없는 경로·뉴스·예약, 비활성 Google 기능 | 타인 예약은 존재 여부 은닉; 기능 상태 확인 |
| 405 HTTP_405 | 지원하지 않는 Method | 정의된 Method로 수정 |
| 409 | 이메일·닉네임 중복, 이미 로그인 | 입력 수정·로그인 상태 전환, 자동 반복 금지 |
| 413 PAYLOAD_TOO_LARGE | Content-Length 1 MiB 초과 | 본문 축소 |
| 422 VALIDATION_ERROR | 스키마·업무 규칙 실패 | 필수값·길이·허용값·예약 상한 등을 수정 |
| 429 TOO_MANY_ATTEMPTS | 인증 실패 제한 초과 | 대기 후 사용자 재시도; 계정 존재 추측 안내 금지 |
| 500 INTERNAL_ERROR | 미처리 예외를 미들웨어에서 일반화 | request_id 보관, 조회는 재시도 가능; 쓰기는 저장 결과 조회 후 판단 |
| 502 CRON_JOB_ORG_UNAVAILABLE | 외부 예약 등록·수정·삭제 실패 | 결과 재조회 후 사용자 재시도 |
| 503 NOT_READY | readyz의 DB 또는 설정된 Redis 준비 실패 | 서비스 복구 대기; readiness와 keepalive 구분 |

`SOURCE_UNAVAILABLE`·`RATE_LIMITED`·`DEPENDENCY_UNAVAILABLE` 등 이전 개념 코드를 현재 공통 코드로 사용하지 않는다. 부분 수집·요약 부족은 성공 응답의 메타·처리 상태로 구분하며 HTTP 200 자체를 오류로 단정하지 않는다. OAuth callback은 오류도 302 후 `#google_error=...`로 전달하므로 일반 JSON 오류와 별개다.


## 3. 전체 엔드포인트
| Method | URL | 인증 | 성공 | 응답 모델 |
|---|---|---|---|---|
| GET | /v1/auth/nickname-availability | 공개 / 선택적 인증 | 200 | NicknameAvailability |
| POST | /v1/auth/signup | 공개 / 선택적 인증 | 201 | AuthResponse |
| POST | /v1/auth/login | 공개 / 선택적 인증 | 200 | AuthResponse |
| POST | /v1/auth/refresh | 공개 / 선택적 인증 | 200 | TokenPair |
| POST | /v1/auth/logout | Bearer access token 필수 | 200 | ResultResponse |
| GET | /healthz | 공개 / 선택적 인증 | 200 | HealthResponse |
| GET | /readyz | 공개 / 선택적 인증 | 200 | HealthResponse |
| GET | /v1/internal/keepalive | 공개 / 선택적 인증 | 200 | KeepAliveResponse |
| GET | /v1/interests/catalog | 공개 / 선택적 인증 | 200 | CatalogResponse |
| GET | /v1/me/interests | Bearer access token 필수 | 200 | MyInterestsResponse |
| PUT | /v1/me/interests | Bearer access token 필수 | 200 | MyInterestsResponse |
| GET | /v1/me/session | 공개 / 선택적 인증 | 200 | SessionResponse |
| PATCH | /v1/me/nickname | Bearer access token 필수 | 200 | NicknameResult |
| DELETE | /v1/me | Bearer access token 필수 | 200 | ResultResponse |
| GET | /v1/news | 공개 / 선택적 인증 | 200 | NewsListResponse |
| GET | /v1/news/activity | Bearer access token 필수 | 200 | NewsActivity |
| GET | /v1/news/read-state | Bearer access token 필수 | 200 | list[str] |
| PUT | /v1/news/{news_id}/read | Bearer access token 필수 | 204 | Response |
| GET | /v1/news/{news_id} | 공개 / 선택적 인증 | 200 | NewsDetailResponse |
| POST | /v1/internal/scheduler/tick | Bearer SCHEDULER_TICK_SECRET 필수 (사용자 JWT 아님) | 200 | TickResponse |
| GET | /v1/me/schedule-runs | Bearer access token 필수 | 200 | ScheduleRunListResponse |
| POST | /v1/me/schedule-runs/seen | Bearer access token 필수 | 204 | Response |
| GET | /v1/me/settings | Bearer access token 필수 | 200 | SettingsResponse |
| PATCH | /v1/me/settings | Bearer access token 필수 | 200 | SettingsResponse |
| GET | /v1/me/schedules | Bearer access token 필수 | 200 | ScheduleListResponse |
| POST | /v1/me/schedules | Bearer access token 필수 | 201 | ScheduleResponse |
| PATCH | /v1/me/schedules/{schedule_id} | Bearer access token 필수 | 200 | ScheduleResponse |
| DELETE | /v1/me/schedules/{schedule_id} | Bearer access token 필수 | 204 | Response |
| GET | /v1/auth/google/status | 공개 / 선택적 인증 | 200 | dict[str, bool] |
| GET | /v1/auth/google/login | 공개 / 선택적 인증 | 302 | RedirectResponse |
| GET | /v1/auth/google/callback | 공개 / 선택적 인증 | 302 | RedirectResponse |
| POST | /v1/auth/google/exchange | 공개 / 선택적 인증 | 200 | AuthResponse |
| POST | /v1/auth/google/link | 공개 / 선택적 인증 | 200 | AuthResponse |


## 4. API별 상세 계약

각 모델의 모든 필드·타입·필수·기본값·제약과 검증된 JSON 예시는 5절에 정의한다. 경계 모델 외 주입 의존성은 HTTP 파라미터에 포함하지 않는다. 응답 모델의 nullable 필드는 생략 가능 여부와 별개로 표기한다.


### 4.1. GET `/v1/auth/nickname-availability`

표시용 닉네임의 사용 가능 여부를 확인한다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `NicknameAvailability`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/auth_routes.py:32`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Query | nickname | Nickname: string, 정규화 후 2~30자 | 필수 |


- 닉네임 형식 오류는 422 VALIDATION_ERROR. 중복 확인은 200 응답의 available=false로 안내하며, 실제 가입·변경에서 DB 고유성을 다시 검사한다.


### 4.2. POST `/v1/auth/signup`

이메일·비밀번호로 가입하고 로그인 토큰을 받는다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 201 / `AuthResponse`
- 요청 본문: SignupRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/auth_routes.py:62`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | SignupRequest | 필수 |


- 201 AuthResponse. 이메일 중복 409 EMAIL_ALREADY_REGISTERED, 닉네임 중복 409 NICKNAME_TAKEN, 흔한 비밀번호 422 WEAK_PASSWORD, 이미 로그인 409 ALREADY_LOGGED_IN.
- 프론트는 가입 후 이메일을 채운 로그인 팝업으로 전환한다. 가입 API의 토큰 반환과 UI 로그인 완료를 동일시하지 않는다.


### 4.3. POST `/v1/auth/login`

이메일·비밀번호로 로그인하고 토큰을 받는다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `AuthResponse`
- 요청 본문: LoginRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/auth_routes.py:87`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | LoginRequest | 필수 |


- 이메일 없음과 비밀번호 오류를 같은 401 INVALID_CREDENTIALS로 응답. 누적 실패 429 TOO_MANY_ATTEMPTS, 이미 로그인 409.
- 성공 시 onboarding_required=true이면 /settings.html?welcome=1#interests, 아니면 /?language=ko로 이동한다.


### 4.4. POST `/v1/auth/refresh`

refresh 토큰으로 새 access·refresh 토큰을 받는다(로그인 유지).

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `TokenPair`
- 요청 본문: RefreshRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/auth_routes.py:110`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | RefreshRequest | 필수 |


- refresh token 회전. 만료·재사용은 401, 재사용 탐지 시 같은 family의 토큰을 폐기한다.


### 4.5. POST `/v1/auth/logout`

로그아웃: 이 사용자의 refresh 토큰을 모두 폐기한다.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `ResultResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/auth_routes.py:125`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 해당 사용자의 모든 refresh 토큰을 폐기한다. access 토큰의 단순 클라이언트 제거와 구분한다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.6. GET `/healthz`

프로세스가 살아 있는지 알려 준다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `HealthResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/health_routes.py:23`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.





### 4.7. GET `/readyz`

요청을 받을 준비가 됐는지(DB 연결) 알려 준다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `HealthResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/health_routes.py:37`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- DB 및 설정된 Redis 준비 상태 확인; 실패는 503 NOT_READY. 미설정 Redis는 메모리 fallback으로 허용한다.


### 4.8. GET `/v1/internal/keepalive`

외부 cron의 keep-alive ping 전용. DB·Redis를 거치지 않고 즉시 200을 반환한다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `KeepAliveResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/health_routes.py:51`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 인증 없이 200, no-store. 준비 상태나 외부 의존성을 검사하지 않는다. OpenAPI 표시 제외 경로지만 이 문서에는 포함한다.


### 4.9. GET `/v1/interests/catalog`

선택 가능한 관심사 15개를 대주제별로 알려 준다(로그인 불필요).

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `CatalogResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/interest_routes.py:20`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 현재 카탈로그는 InterestCode enum 30개(한국어·영문 각 15개). PUT은 전체 교체, 중복·알 수 없는 코드·30개 초과는 422; 빈 배열은 선택 해제.


### 4.10. GET `/v1/me/interests`

내 관심사를 조회한다.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `MyInterestsResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/interest_routes.py:34`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 현재 카탈로그는 InterestCode enum 30개(한국어·영문 각 15개). PUT은 전체 교체, 중복·알 수 없는 코드·30개 초과는 422; 빈 배열은 선택 해제.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.11. PUT `/v1/me/interests`

내 관심사를 보낸 목록으로 통째로 교체한다.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `MyInterestsResponse`
- 요청 본문: InterestsUpdateRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/interest_routes.py:51`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | InterestsUpdateRequest | 필수 |


- 현재 카탈로그는 InterestCode enum 30개(한국어·영문 각 15개). PUT은 전체 교체, 중복·알 수 없는 코드·30개 초과는 422; 빈 배열은 선택 해제.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.12. GET `/v1/me/session`

로그인 상태를 알려 준다(화면의 메뉴 노출 판단용).

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `SessionResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/me_routes.py:29`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 토큰 없음·만료·잘못된 토큰은 200 authenticated=false, user=null. 로그인 시 interests도 포함.


### 4.13. PATCH `/v1/me/nickname`

로그인한 본인의 닉네임을 갱신한다.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `NicknameResult`
- 요청 본문: NicknameUpdate; 필수
- 구현 근거: `src/backend/src/dait/api/v1/me_routes.py:52`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | NicknameUpdate | 필수 |


- 닉네임 null 또는 빈 문자열은 제거. 2~30자 검증, 중복은 409 NICKNAME_TAKEN (기존 문서의 422 중복 설명 수정).
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.14. DELETE `/v1/me`

회원탈퇴: 본인 확인 뒤 계정과 토큰을 실제로 삭제한다.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `ResultResponse`
- 요청 본문: WithdrawRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/me_routes.py:70`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | WithdrawRequest | 필수 |


- 비밀번호 계정은 password로 재인증. Google 전용 계정은 confirm_text="탈퇴" 및 access 토큰 발급 5분 이내 조건 필요; 미충족은 403 RECENT_LOGIN_REQUIRED.
- 성공은 200 {"result":"done"}; 계정 관련 데이터 삭제 후 프론트 토큰을 비우고 비로그인 메인으로 이동. 비밀번호 오류 401, 실패 누적 429.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.15. GET `/v1/news`

뉴스 목록·검색·정렬

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `NewsListResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/news_routes.py:32`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Query | language | Annotated[str \| None, Query(pattern='^(ko\|en)$')] | None |
| Query | topic | Annotated[str \| None, Query(max_length=50)] | None |
| Query | personalized | bool | False |
| Query | interest | Annotated[str \| None, Query(max_length=50)] | None |
| Query | category | Annotated[NewsCategory \| None, Query()] | None |
| Query | q | Annotated[str, Query(max_length=100)] | '' |
| Query | sort | Annotated[SortOrder, Query()] | 'rank' |
| Query | page_size | Annotated[int, Query(ge=1, le=50)] | 10 |
| Query | cursor | Annotated[str \| None, Query(max_length=500)] | None |
| Query | refresh | bool | False |


- 비로그인은 sort=latest·최대 10건, cursor는 422; page.has_more=false. topic·personalized 등 개인화 조건은 비로그인 분기에서 적용하지 않는다.
- 로그인 시 personalized=true는 저장 관심사 OR 집계; interest는 그 범위에서 저장 코드 확인. topic은 카탈로그 키워드 코드 검사 후 최종 scope를 덮어쓴다.
- 현재 language=ko|en과 refresh:bool 쿼리가 구현돼 있다. refresh는 조회 경로의 갱신 제어 입력이며 LLM 직접 호출을 의미하지 않는다.
- READY/INSUFFICIENT 공개 가능. 목록 있음+partial=false 정상, partial=true 부분 지연, 빈 목록은 검색/수집 없음, 네트워크 실패는 연결 안내.


### 4.16. GET `/v1/news/activity`

Fresh filtered counts and private read state, never publicly cached.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `NewsActivity`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/news_routes.py:108`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Query | q | Annotated[str, Query(max_length=100)] | '' |
| Query | ids | Annotated[list[str] \| None, Query(max_length=50)] | None |
| Query | language | Annotated[str \| None, Query(pattern='^(ko\|en)$')] | None |
| Query | personalized | bool | False |


- 본인 읽음·관심사 정보를 반환하므로 인증 필수 및 Cache-Control: no-store. ids는 최대 50개, 각 ID 1~64자.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.17. GET `/v1/news/read-state`

Fetch private read receipts independently of public topic counts.

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `list[str]`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/news_routes.py:125`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Query | ids | Annotated[list[str] \| None, Query(max_length=50)] | None |


- 본인 읽음·관심사 정보를 반환하므로 인증 필수 및 Cache-Control: no-store. ids는 최대 50개, 각 ID 1~64자.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


```json
[
  "00000000-0000-4000-8000-000000000001"
]
```


### 4.18. PUT `/v1/news/{news_id}/read`

Idempotent authenticated read receipt.

- 인증: Bearer access token 필수
- 성공: HTTP 204 / `Response`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/news_routes.py:139`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Path | news_id | str | 필수 |


- 공개 가능한 뉴스의 읽음 기록은 멱등이며 성공 시 204(본문 없음)다. 존재하지 않거나 공개 불가능한 뉴스는 mark_read()에서 404 NEWS_NOT_FOUND로 거부한다. news_id가 비어 있거나 64자 초과이면 라우트에서 422 VALIDATION_ERROR다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


성공 응답 본문 없음.


### 4.19. GET `/v1/news/{news_id}`

뉴스 상세

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `NewsDetailResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/news_routes.py:152`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Path | news_id | str | 필수 |


- 없는 또는 비공개 뉴스는 404 NEWS_NOT_FOUND. 상세 API는 제공하지만 내부 상세 UI는 미제공이다.


### 4.20. POST `/v1/internal/scheduler/tick`

외부 cron tick 수신(내부 전용)

- 인증: Bearer SCHEDULER_TICK_SECRET 필수 (사용자 JWT 아님)
- 성공: HTTP 200 / `TickResponse`
- 요청 본문: TickRequest | None; 생략 가능
- 구현 근거: `src/backend/src/dait/api/v1/scheduler_routes.py:54`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Header | authorization | Annotated[str \| None, Header()] | None |
| JSON body | body | TickRequest \| None | None |


- 사용자 JWT 대신 SCHEDULER_TICK_SECRET, 잘못된 비밀값은 401 AUTHENTICATION_FAILED. 응답 뒤 BackgroundTasks로 검색·전송 처리. dedupe·lease로 중복 실행 방지.
- 실제 실행 저장소는 schedule_runs·schedule_run_items이다. 응답 jobs_created 이름은 회차 생성 수를 뜻하는 호환 필드로 읽으며 jobs 테이블에 반드시 새 행을 넣는다고 해석하지 않는다.


### 4.21. GET `/v1/me/schedule-runs`

내 예약 검색 결과·실행 이력

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `ScheduleRunListResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/scheduler_routes.py:86`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 실행 이력은 ScheduleRunListResponse(unseen, items), 기존 문서의 has_more는 현재 모델에 없다. 검색·알림 상태는 schedule_run.py enum을 따른다. seen 호출은 본문 없이 본인 이력을 확인 처리한다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.22. POST `/v1/me/schedule-runs/seen`

예약 검색 결과 확인 표시

- 인증: Bearer access token 필수
- 성공: HTTP 204 / `Response`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/scheduler_routes.py:92`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 실행 이력은 ScheduleRunListResponse(unseen, items), 기존 문서의 has_more는 현재 모델에 없다. 검색·알림 상태는 schedule_run.py enum을 따른다. seen 호출은 본문 없이 본인 이력을 확인 처리한다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


성공 응답 본문 없음.


### 4.23. GET `/v1/me/settings`

내 설정 조회

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `SettingsResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:31`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 내 설정만 조회·변경. 미전송 PATCH 필드는 유지한다. 카테고리는 활성 AI·ECONOMY·POLITICS, 기본 노출은 5 또는 10. UI 미제공 필드와 API 유지 계약을 구분한다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.24. PATCH `/v1/me/settings`

내 설정 저장

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `SettingsResponse`
- 요청 본문: SettingsUpdateRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:42`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | SettingsUpdateRequest | 필수 |


- 내 설정만 조회·변경. 미전송 PATCH 필드는 유지한다. 카테고리는 활성 AI·ECONOMY·POLITICS, 기본 노출은 5 또는 10. UI 미제공 필드와 API 유지 계약을 구분한다.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.25. GET `/v1/me/schedules`

예약 목록

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `ScheduleListResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:57`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- 타인 또는 없는 예약은 404 SCHEDULE_NOT_FOUND. POST는 사용자당 5개 상한. PATCH 빈 변경·시간·시간대·미승인 출처는 422.
- criteria.interests=null은 실행 시점에 저장된 유효한 관심사 중 en.*를 제외한 한국어 코드만 자동 반영한다. 명시적인 배열은 스냅샷으로 사용하며, []는 관심사 우선 검색을 끄지만 카테고리 검색까지 끄는 것은 아니다.
- 현재 DbNewsSearcher는 criteria.source_ids를 저장·검증하지만 검색 조건에는 적용하지 않는다. 관심사 검색 결과가 한도보다 적으면 criteria.categories·keywords 기반 조회로 부족분을 보충하므로 관심사에만 일치하는 기사로 제한되지 않는다. 결과를 중복 제거하고 발행 시각·뉴스 ID 역순으로 정렬한다.
- cron-job.org 구성 시 예약별 외부 job 연동, 실패는 502.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.26. POST `/v1/me/schedules`

예약 생성

- 인증: Bearer access token 필수
- 성공: HTTP 201 / `ScheduleResponse`
- 요청 본문: ScheduleCreateRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:68`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | ScheduleCreateRequest | 필수 |


- 타인 또는 없는 예약은 404 SCHEDULE_NOT_FOUND. POST는 사용자당 5개 상한. PATCH 빈 변경·시간·시간대·미승인 출처는 422.
- criteria.interests=null은 실행 시점에 저장된 유효한 관심사 중 en.*를 제외한 한국어 코드만 자동 반영한다. 명시적인 배열은 스냅샷으로 사용하며, []는 관심사 우선 검색을 끄지만 카테고리 검색까지 끄는 것은 아니다.
- 현재 DbNewsSearcher는 criteria.source_ids를 저장·검증하지만 검색 조건에는 적용하지 않는다. 관심사 검색 결과가 한도보다 적으면 criteria.categories·keywords 기반 조회로 부족분을 보충하므로 관심사에만 일치하는 기사로 제한되지 않는다. 결과를 중복 제거하고 발행 시각·뉴스 ID 역순으로 정렬한다.
- cron-job.org 구성 시 예약별 외부 job 연동, 실패는 502.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.27. PATCH `/v1/me/schedules/{schedule_id}`

예약 수정

- 인증: Bearer access token 필수
- 성공: HTTP 200 / `ScheduleResponse`
- 요청 본문: ScheduleUpdateRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:87`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Path | schedule_id | str | 필수 |
| JSON body | body | ScheduleUpdateRequest | 필수 |


- 타인 또는 없는 예약은 404 SCHEDULE_NOT_FOUND. POST는 사용자당 5개 상한. PATCH 빈 변경·시간·시간대·미승인 출처는 422.
- criteria.interests=null은 실행 시점에 저장된 유효한 관심사 중 en.*를 제외한 한국어 코드만 자동 반영한다. 명시적인 배열은 스냅샷으로 사용하며, []는 관심사 우선 검색을 끄지만 카테고리 검색까지 끄는 것은 아니다.
- 현재 DbNewsSearcher는 criteria.source_ids를 저장·검증하지만 검색 조건에는 적용하지 않는다. 관심사 검색 결과가 한도보다 적으면 criteria.categories·keywords 기반 조회로 부족분을 보충하므로 관심사에만 일치하는 기사로 제한되지 않는다. 결과를 중복 제거하고 발행 시각·뉴스 ID 역순으로 정렬한다.
- cron-job.org 구성 시 예약별 외부 job 연동, 실패는 502.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


### 4.28. DELETE `/v1/me/schedules/{schedule_id}`

예약 삭제

- 인증: Bearer access token 필수
- 성공: HTTP 204 / `Response`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/settings_routes.py:109`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Path | schedule_id | str | 필수 |


- 타인 또는 없는 예약은 404 SCHEDULE_NOT_FOUND. POST는 사용자당 5개 상한. PATCH 빈 변경·시간·시간대·미승인 출처는 422.
- criteria.interests=null은 실행 시점에 저장된 유효한 관심사 중 en.*를 제외한 한국어 코드만 자동 반영한다. 명시적인 배열은 스냅샷으로 사용하며, []는 관심사 우선 검색을 끄지만 카테고리 검색까지 끄는 것은 아니다.
- 현재 DbNewsSearcher는 criteria.source_ids를 저장·검증하지만 검색 조건에는 적용하지 않는다. 관심사 검색 결과가 한도보다 적으면 criteria.categories·keywords 기반 조회로 부족분을 보충하므로 관심사에만 일치하는 기사로 제한되지 않는다. 결과를 중복 제거하고 발행 시각·뉴스 ID 역순으로 정렬한다.
- cron-job.org 구성 시 예약별 외부 job 연동, 실패는 502.
- 공통 인증 실패 401 INVALID_TOKEN. 그 외 400·413·422·500은 공통 처리 규칙을 따른다.


성공 응답 본문 없음.


### 4.29. GET `/v1/auth/google/status`

Expose availability only; credentials remain on the server.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `dict[str, bool]`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/social_routes.py:46`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- Google 설정 존재 여부에 따라 동작. status는 enabled만 공개. 비활성 login/callback/exchange/link는 404 SOCIAL_LOGIN_DISABLED.
- login은 state 쿠키(10분)와 302. callback은 state·nonce·PKCE 검증 후 60초 1회용 교환 코드 또는 연결 ticket·오류 fragment로 302; access/refresh 토큰을 URL로 전달하지 않는다.
- exchange/link는 AuthResponse. 코드·ticket 만료/재사용은 401; link 비밀번호 실패는 401 및 제한 초과 429. provider 응답 추가 필드는 내부 전용 모델에서 무시한다.


```json
{
  "enabled": false
}
```


### 4.30. GET `/v1/auth/google/login`

구글 로그인을 시작한다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 302 / `RedirectResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/social_routes.py:52`


Path·Query·JSON body 입력 없음. 인증 헤더는 위 인증 정책을 따른다.


- Google 설정 존재 여부에 따라 동작. status는 enabled만 공개. 비활성 login/callback/exchange/link는 404 SOCIAL_LOGIN_DISABLED.
- login은 state 쿠키(10분)와 302. callback은 state·nonce·PKCE 검증 후 60초 1회용 교환 코드 또는 연결 ticket·오류 fragment로 302; access/refresh 토큰을 URL로 전달하지 않는다.
- exchange/link는 AuthResponse. 코드·ticket 만료/재사용은 401; link 비밀번호 실패는 401 및 제한 초과 429. provider 응답 추가 필드는 내부 전용 모델에서 무시한다.


```http
HTTP/1.1 302 Found
Location: <검증된 리다이렉트 대상>
Cache-Control: no-store
```


### 4.31. GET `/v1/auth/google/callback`

구글 로그인 결과를 받아 화면으로 돌려보낸다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 302 / `RedirectResponse`
- 요청 본문: 없음
- 구현 근거: `src/backend/src/dait/api/v1/social_routes.py:84`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| Query | state | Annotated[str \| None, Query(max_length=128)] | None |
| Query | code | Annotated[str \| None, Query(max_length=2048)] | None |
| Query | error | Annotated[str \| None, Query(max_length=100)] | None |
| Cookie | cookie_state | Annotated[str \| None, Cookie(alias=_COOKIE, max_length=128)] | None |


- Google 설정 존재 여부에 따라 동작. status는 enabled만 공개. 비활성 login/callback/exchange/link는 404 SOCIAL_LOGIN_DISABLED.
- login은 state 쿠키(10분)와 302. callback은 state·nonce·PKCE 검증 후 60초 1회용 교환 코드 또는 연결 ticket·오류 fragment로 302; access/refresh 토큰을 URL로 전달하지 않는다.
- exchange/link는 AuthResponse. 코드·ticket 만료/재사용은 401; link 비밀번호 실패는 401 및 제한 초과 429. provider 응답 추가 필드는 내부 전용 모델에서 무시한다.


```http
HTTP/1.1 302 Found
Location: <검증된 리다이렉트 대상>
Cache-Control: no-store
```


### 4.32. POST `/v1/auth/google/exchange`

교환 코드를 로그인 토큰으로 바꾼다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `AuthResponse`
- 요청 본문: ExchangeRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/social_routes.py:129`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | ExchangeRequest | 필수 |


- Google 설정 존재 여부에 따라 동작. status는 enabled만 공개. 비활성 login/callback/exchange/link는 404 SOCIAL_LOGIN_DISABLED.
- login은 state 쿠키(10분)와 302. callback은 state·nonce·PKCE 검증 후 60초 1회용 교환 코드 또는 연결 ticket·오류 fragment로 302; access/refresh 토큰을 URL로 전달하지 않는다.
- exchange/link는 AuthResponse. 코드·ticket 만료/재사용은 401; link 비밀번호 실패는 401 및 제한 초과 429. provider 응답 추가 필드는 내부 전용 모델에서 무시한다.


### 4.33. POST `/v1/auth/google/link`

같은 이메일의 기존 계정에 구글 계정을 연결하고 로그인한다.

- 인증: 공개 / 선택적 인증
- 성공: HTTP 200 / `AuthResponse`
- 요청 본문: LinkRequest; 필수
- 구현 근거: `src/backend/src/dait/api/v1/social_routes.py:149`


| 위치 | 이름 | 타입·제약 | 기본값/필수 |
|---|---|---|---|
| JSON body | body | LinkRequest | 필수 |


- Google 설정 존재 여부에 따라 동작. status는 enabled만 공개. 비활성 login/callback/exchange/link는 404 SOCIAL_LOGIN_DISABLED.
- login은 state 쿠키(10분)와 302. callback은 state·nonce·PKCE 검증 후 60초 1회용 교환 코드 또는 연결 ticket·오류 fragment로 302; access/refresh 토큰을 URL로 전달하지 않는다.
- exchange/link는 AuthResponse. 코드·ticket 만료/재사용은 401; link 비밀번호 실패는 401 및 제한 초과 429. provider 응답 추가 필드는 내부 전용 모델에서 무시한다.


## 5. 요청·응답 모델 사전과 예시

다음 표는 실제 Pydantic 모델의 JSON Schema에서 추출했다. 필수 여부는 required 기준이며, nullable과 독립적이다. 기본값 “생성기”는 default_factory이며 DB 기본값과 다르다. 예시값은 가짜 데이터이고 실제 모델 검증을 통과했다. 문자열 정규화·업무 검증은 서비스 규칙 및 6절 코드와 함께 읽는다.


### ArticleInfo

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | 추가 JSON Schema 제약 없음 | id |
| title | string | Y | "없음" | {"value.maxLength": 500} | title |
| source_name | string | Y | "없음" | {"value.maxLength": 200} | source_name |
| published_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | published_at |
| original_language | string | Y | "없음" | {"value.maxLength": 8, "value.minLength": 2} | original_language |
| translation_required | boolean | N | false | 추가 JSON Schema 제약 없음 | translation_required |
| category | NewsCategory | Y | "없음" | {"value.reference": "NewsCategory", "value.enum": ["AI", "WEATHER", "ECONOMY", "POLITICS"]} | category |
| estimated_read_minutes | integer \| null | N | null | {"value.anyOf0.minimum": 1} | estimated_read_minutes |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "title": "example",
  "source_name": "example",
  "published_at": "2026-11-16T00:00:00Z",
  "original_language": "ko",
  "category": "AI"
}
```


### AuthResponse

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| user | UserPublic | Y | "없음" | {"value.reference": "UserPublic"} | user |
| tokens | TokenPair | Y | "없음" | {"value.reference": "TokenPair"} | tokens |
| onboarding_required | boolean | N | false | 추가 JSON Schema 제약 없음 | onboarding_required |
| interests | list[InterestItem] | N | "생성기" | {"value[].reference": "InterestItem"} | interests |

```json
{
  "user": {
    "id": "00000000-0000-4000-8000-000000000001",
    "email": "reader@example.com",
    "status": "ACTIVE",
    "role": "USER",
    "nickname": "news_reader"
  },
  "tokens": {
    "access_token": "example",
    "refresh_token": "example_refresh_token_1234567890"
  },
  "onboarding_required": false,
  "interests": [
    {
      "code": "ai.models",
      "name": "example",
      "group": "example"
    }
  ]
}
```


### CatalogResponse

구현: `dait/schemas/interest.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| groups | list[InterestGroup] | Y | "없음" | {"value[].reference": "InterestGroup"} | groups |

```json
{
  "groups": [
    {
      "group": "example",
      "group_name": "example",
      "interests": [
        {
          "code": "ai.models",
          "name": "example",
          "group": "example"
        }
      ]
    }
  ]
}
```


### ContentInfo

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| summary_lines | list[string] | Y | "없음" | {"value.maxItems": 3, "value[].maxLength": 500} | summary_lines |
| translated_text | string \| null | N | null | {"value.anyOf0.maxLength": 20000} | translated_text |
| processed_at | string (date-time) \| null | N | null | {"value.anyOf0.format": "date-time"} | processed_at |
| content_status | enum(READY, INSUFFICIENT, FAILED, PENDING) | Y | "없음" | {"value.enum": ["READY", "INSUFFICIENT", "FAILED", "PENDING"]} | content_status |
| summary_model_version | string \| null | N | null | {"value.anyOf0.maxLength": 80} | summary_model_version |

```json
{
  "summary_lines": [
    "example"
  ],
  "content_status": "READY"
}
```


### ExchangeRequest

구현: `dait/schemas/social.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| code | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 20} | code |

```json
{
  "code": "example_one_time_code_1234567890"
}
```


### HealthResponse

구현: `dait/schemas/health.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| status | enum(ok, ready) | Y | "없음" | {"value.enum": ["ok", "ready"]} | status |

```json
{
  "status": "ok"
}
```


### InterestGroup

구현: `dait/schemas/interest.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| group | string | Y | "없음" | 추가 JSON Schema 제약 없음 | group |
| group_name | string | Y | "없음" | 추가 JSON Schema 제약 없음 | group_name |
| interests | list[InterestItem] | Y | "없음" | {"value[].reference": "InterestItem"} | interests |

```json
{
  "group": "example",
  "group_name": "example",
  "interests": [
    {
      "code": "ai.models",
      "name": "example",
      "group": "example"
    }
  ]
}
```


### InterestItem

구현: `dait/schemas/interest.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| code | InterestCode | Y | "없음" | {"value.reference": "InterestCode", "value.enum": ["ai.models", "ai.agents", "ai.devtools", "ai.opensource", "ai.infra", "economy.industry", "economy.business", "economy.startups", "economy.markets", "economy.jobs", "society.policy", "society.education", "society.health", "society.climate", "society.culture", "en.ai.models", "en.ai.agents", "en.ai.devtools", "en.ai.opensource", "en.ai.infra", "en.economy.industry", "en.economy.business", "en.economy.startups", "en.economy.markets", "en.economy.jobs", "en.society.policy", "en.society.education", "en.society.health", "en.society.climate", "en.society.culture"]} | code |
| name | string | Y | "없음" | 추가 JSON Schema 제약 없음 | name |
| group | string | Y | "없음" | 추가 JSON Schema 제약 없음 | group |

```json
{
  "code": "ai.models",
  "name": "example",
  "group": "example"
}
```


### InterestsUpdateRequest

구현: `dait/schemas/interest.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| interests | list[InterestCode] | N | "생성기" | {"value.maxItems": 30, "value[].reference": "InterestCode", "value[].enum": ["ai.models", "ai.agents", "ai.devtools", "ai.opensource", "ai.infra", "economy.industry", "economy.business", "economy.startups", "economy.markets", "economy.jobs", "society.policy", "society.education", "society.health", "society.climate", "society.culture", "en.ai.models", "en.ai.agents", "en.ai.devtools", "en.ai.opensource", "en.ai.infra", "en.economy.industry", "en.economy.business", "en.economy.startups", "en.economy.markets", "en.economy.jobs", "en.society.policy", "en.society.education", "en.society.health", "en.society.climate", "en.society.culture"]} | interests |

```json
{
  "interests": [
    "ai.models"
  ]
}
```


### KeepAliveResponse

구현: `dait/schemas/health.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| status | 'ok' | N | "ok" | {"value.const": "ok"} | status |
| service | string | N | "dait" | 추가 JSON Schema 제약 없음 | service |
| time | string | Y | "없음" | 추가 JSON Schema 제약 없음 | time |

```json
{
  "time": "example"
}
```


### LinkRequest

구현: `dait/schemas/social.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| ticket | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 20} | ticket |
| password | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 1} | password |

```json
{
  "ticket": "example_one_time_code_1234567890",
  "password": "Demo!S7ecure2026$"
}
```


### LoginRequest

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| email | string (email) | Y | "없음" | {"value.format": "email"} | email |
| password | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 1} | password |

```json
{
  "email": "reader@example.com",
  "password": "Demo!S7ecure2026$"
}
```


### MyInterestsResponse

구현: `dait/schemas/interest.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| interests | list[InterestItem] | Y | "없음" | {"value[].reference": "InterestItem"} | interests |

```json
{
  "interests": [
    {
      "code": "ai.models",
      "name": "example",
      "group": "example"
    }
  ]
}
```


### NewsActivity

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| interest_counts | dict[str, integer] | N | "생성기" | 추가 JSON Schema 제약 없음 | interest_counts |
| total | integer | Y | "없음" | {"value.minimum": 0} | total |
| counts | dict[str, integer] | Y | "없음" | {"value{value}.minimum": 0} | counts |
| read_ids | list[string] | Y | "없음" | {"value.maxItems": 50, "value[].maxLength": 64, "value[].minLength": 1} | read_ids |

```json
{
  "total": 1,
  "counts": {},
  "read_ids": [
    "example_"
  ]
}
```


### NewsDetailResponse

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| article | ArticleInfo | Y | "없음" | {"value.reference": "ArticleInfo"} | article |
| content | ContentInfo | Y | "없음" | {"value.reference": "ContentInfo"} | content |
| source | SourceInfo | Y | "없음" | {"value.reference": "SourceInfo"} | source |
| related_news | list[RelatedNewsItem] | Y | "없음" | {"value.maxItems": 10, "value[].reference": "RelatedNewsItem"} | related_news |
| processing | ProcessingInfo | Y | "없음" | {"value.reference": "ProcessingInfo"} | processing |

```json
{
  "article": {
    "id": "00000000-0000-4000-8000-000000000001",
    "title": "example",
    "source_name": "example",
    "published_at": "2026-11-16T00:00:00Z",
    "original_language": "ko",
    "category": "AI"
  },
  "content": {
    "summary_lines": [
      "example"
    ],
    "content_status": "READY"
  },
  "source": {
    "original_url": "https://example.com/news/1",
    "url_verified": false,
    "source_type": "example_"
  },
  "related_news": [
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "title": "example",
      "source_name": "example",
      "published_at": "2026-11-16T00:00:00Z",
      "reason": "example_",
      "score": 1
    }
  ],
  "processing": {
    "collection_status": "SUCCEEDED",
    "translation_status": "SUCCEEDED",
    "summary_status": "SUCCEEDED"
  }
}
```


### NewsListItem

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | {"value.maxLength": 64, "value.minLength": 1} | id |
| original_language | string | N | "und" | 추가 JSON Schema 제약 없음 | original_language |
| author_name | string \| null | N | null | 추가 JSON Schema 제약 없음 | author_name |
| rank | integer | Y | "없음" | {"value.minimum": 1} | rank |
| title | string | Y | "없음" | {"value.maxLength": 500, "value.minLength": 1} | title |
| source_name | string | Y | "없음" | {"value.maxLength": 200, "value.minLength": 1} | source_name |
| published_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | published_at |
| category | NewsCategory | Y | "없음" | {"value.reference": "NewsCategory", "value.enum": ["AI", "WEATHER", "ECONOMY", "POLITICS"]} | category |
| summary_lines | list[string] | Y | "없음" | {"value.maxItems": 3, "value[].maxLength": 500} | summary_lines |
| processing_status | enum(READY, INSUFFICIENT, FAILED, PENDING) | Y | "없음" | {"value.enum": ["READY", "INSUFFICIENT", "FAILED", "PENDING"]} | processing_status |
| original_url | string | Y | "없음" | {"value.maxLength": 2000, "value.minLength": 1} | original_url |
| is_partial | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | is_partial |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "rank": 1,
  "title": "example_",
  "source_name": "example_",
  "published_at": "2026-11-16T00:00:00Z",
  "category": "AI",
  "summary_lines": [
    "example"
  ],
  "processing_status": "READY",
  "original_url": "https://example.com/news/1",
  "is_partial": false
}
```


### NewsListMeta

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| total_visible | integer | Y | "없음" | {"value.minimum": 0} | total_visible |
| partial | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | partial |
| message | string \| null | N | null | {"value.anyOf0.maxLength": 200} | message |
| rank_basis | list[string] | Y | "없음" | {"value.maxItems": 10} | rank_basis |

```json
{
  "total_visible": 1,
  "partial": false,
  "rank_basis": [
    "example"
  ]
}
```


### NewsListResponse

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| items | list[NewsListItem] | Y | "없음" | {"value.maxItems": 50, "value[].reference": "NewsListItem"} | items |
| page | PageInfo | Y | "없음" | {"value.reference": "PageInfo"} | page |
| meta | NewsListMeta | Y | "없음" | {"value.reference": "NewsListMeta"} | meta |

```json
{
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "rank": 1,
      "title": "example_",
      "source_name": "example_",
      "published_at": "2026-11-16T00:00:00Z",
      "category": "AI",
      "summary_lines": [
        "example"
      ],
      "processing_status": "READY",
      "original_url": "https://example.com/news/1",
      "is_partial": false
    }
  ],
  "page": {
    "has_more": false
  },
  "meta": {
    "total_visible": 1,
    "partial": false,
    "rank_basis": [
      "example"
    ]
  }
}
```


### NicknameAvailability

구현: `dait/schemas/nickname.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| nickname | string | Y | "없음" | {"value.maxLength": 30, "value.minLength": 2} | nickname |
| available | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | available |

```json
{
  "nickname": "news_reader",
  "available": false
}
```


### NicknameResult

구현: `dait/schemas/nickname.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| nickname | string \| null | Y | "없음" | {"value.anyOf0.maxLength": 30, "value.anyOf0.minLength": 2} | nickname |

```json
{
  "nickname": "news_reader"
}
```


### NicknameUpdate

구현: `dait/schemas/nickname.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| nickname | string \| null | Y | "없음" | {"value.anyOf0.maxLength": 30, "value.anyOf0.minLength": 2} | nickname |

```json
{
  "nickname": "news_reader"
}
```


### PageInfo

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| next_cursor | string \| null | N | null | {"value.anyOf0.maxLength": 500} | next_cursor |
| has_more | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | has_more |

```json
{
  "has_more": false
}
```


### ProcessingInfo

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| collection_status | enum(SUCCEEDED, FAILED, PENDING) | Y | "없음" | {"value.enum": ["SUCCEEDED", "FAILED", "PENDING"]} | collection_status |
| translation_status | enum(SUCCEEDED, FAILED, SKIPPED, PENDING) | Y | "없음" | {"value.enum": ["SUCCEEDED", "FAILED", "SKIPPED", "PENDING"]} | translation_status |
| summary_status | enum(SUCCEEDED, FAILED, SKIPPED, PENDING) | Y | "없음" | {"value.enum": ["SUCCEEDED", "FAILED", "SKIPPED", "PENDING"]} | summary_status |

```json
{
  "collection_status": "SUCCEEDED",
  "translation_status": "SUCCEEDED",
  "summary_status": "SUCCEEDED"
}
```


### RefreshRequest

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| refresh_token | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 256, "value.minLength": 20} | refresh_token |

```json
{
  "refresh_token": "example_refresh_token_1234567890"
}
```


### RelatedNewsItem

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | 추가 JSON Schema 제약 없음 | id |
| title | string | Y | "없음" | {"value.maxLength": 500} | title |
| source_name | string | Y | "없음" | {"value.maxLength": 200} | source_name |
| published_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | published_at |
| reason | string | Y | "없음" | {"value.maxLength": 500, "value.minLength": 1} | reason |
| score | number | Y | "없음" | {"value.maximum": 1.0, "value.minimum": 0.0} | score |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "title": "example",
  "source_name": "example",
  "published_at": "2026-11-16T00:00:00Z",
  "reason": "example_",
  "score": 1
}
```


### ResultResponse

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| result | 'done' | N | "done" | {"value.const": "done"} | result |

```json
{}
```


### ScheduleCreateRequest

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| local_time | string | Y | "없음" | {"value.maxLength": 5, "value.minLength": 4, "validator": "값이 null이 아니면 HH:mm 24시간 형식; 00:00~23:59"} | local_time |
| timezone | string | Y | "없음" | {"value.maxLength": 64, "value.minLength": 1, "service": "서비스에서 유효한 IANA 시간대 검사"} | timezone |
| enabled | boolean | N | true | 추가 JSON Schema 제약 없음 | enabled |
| criteria | ScheduleCriteria | Y | "없음" | {"value.reference": "ScheduleCriteria"} | criteria |

```json
{
  "local_time": "08:30",
  "timezone": "Asia/Seoul",
  "criteria": {
    "categories": [
      "AI"
    ],
    "interests": [
      "ai.models"
    ]
  }
}
```


### ScheduleCriteria

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| keywords | list[string] | N | "생성기" | {"value.maxItems": 20, "value[].maxLength": 50, "value[].minLength": 1} | keywords |
| source_ids | list[string] | N | "생성기" | {"value.maxItems": 50, "value[].maxLength": 64, "value[].minLength": 1} | source_ids |
| categories | list[NewsCategory] | Y | "없음" | {"value.maxItems": 10, "value.minItems": 1, "value[].reference": "NewsCategory", "value[].enum": ["AI", "WEATHER", "ECONOMY", "POLITICS"]} | categories |
| interests | list[InterestCode] \| null | N | null | {"value.anyOf0.maxItems": 30, "value.anyOf0[].reference": "InterestCode", "value.anyOf0[].enum": ["ai.models", "ai.agents", "ai.devtools", "ai.opensource", "ai.infra", "economy.industry", "economy.business", "economy.startups", "economy.markets", "economy.jobs", "society.policy", "society.education", "society.health", "society.climate", "society.culture", "en.ai.models", "en.ai.agents", "en.ai.devtools", "en.ai.opensource", "en.ai.infra", "en.economy.industry", "en.economy.business", "en.economy.startups", "en.economy.markets", "en.economy.jobs", "en.society.policy", "en.society.education", "en.society.health", "en.society.climate", "en.society.culture"]} | interests |

```json
{
  "categories": [
    "AI"
  ],
  "interests": [
    "ai.models"
  ]
}
```


실행 동작: source_ids는 저장·검증되지만 현재 예약 검색에는 미적용이다. interests=null 자동 반영은 한국어 코드만 대상이며 명시 배열과 다르다. 관심사 결과 부족 시 categories·keywords로 보충한다.


### ScheduleListResponse

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| items | list[ScheduleResponse] | Y | "없음" | {"value.maxItems": 10, "value[].reference": "ScheduleResponse"} | items |

```json
{
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "local_time": "08:30",
      "timezone": "Asia/Seoul",
      "enabled": false,
      "criteria": {
        "categories": [
          "AI"
        ],
        "interests": [
          "ai.models"
        ]
      },
      "next_run_at": "2026-11-16T00:00:00Z",
      "created_at": "2026-11-16T00:00:00Z",
      "updated_at": "2026-11-16T00:00:00Z"
    }
  ]
}
```


### ScheduleResponse

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | {"value.maxLength": 64, "value.minLength": 1} | id |
| local_time | string | Y | "없음" | {"value.pattern": "^([01]\\d\|2[0-3]):[0-5]\\d$"} | local_time |
| timezone | string | Y | "없음" | {"value.maxLength": 64, "value.minLength": 1} | timezone |
| enabled | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | enabled |
| criteria | ScheduleCriteria | Y | "없음" | {"value.reference": "ScheduleCriteria"} | criteria |
| next_run_at | string (date-time) \| null | Y | "없음" | {"value.anyOf0.format": "date-time"} | next_run_at |
| created_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | created_at |
| updated_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | updated_at |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "local_time": "08:30",
  "timezone": "Asia/Seoul",
  "enabled": false,
  "criteria": {
    "categories": [
      "AI"
    ],
    "interests": [
      "ai.models"
    ]
  },
  "next_run_at": "2026-11-16T00:00:00Z",
  "created_at": "2026-11-16T00:00:00Z",
  "updated_at": "2026-11-16T00:00:00Z"
}
```


### ScheduleRunItem

구현: `dait/schemas/schedule_run.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| news_id | string | Y | "없음" | 추가 JSON Schema 제약 없음 | news_id |
| title | string | Y | "없음" | 추가 JSON Schema 제약 없음 | title |
| source_name | string | Y | "없음" | 추가 JSON Schema 제약 없음 | source_name |
| url | string | Y | "없음" | 추가 JSON Schema 제약 없음 | url |
| published_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | published_at |
| summary_lines | string \| null | N | null | 추가 JSON Schema 제약 없음 | summary_lines |

```json
{
  "news_id": "00000000-0000-4000-8000-000000000001",
  "title": "example",
  "source_name": "example",
  "url": "https://example.com/news/1",
  "published_at": "2026-11-16T00:00:00Z"
}
```


### ScheduleRunListResponse

구현: `dait/schemas/schedule_run.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| unseen | integer | Y | "없음" | 추가 JSON Schema 제약 없음 | unseen |
| items | list[ScheduleRunResponse] | Y | "없음" | {"value[].reference": "ScheduleRunResponse"} | items |

```json
{
  "unseen": 1,
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "schedule_id": "00000000-0000-4000-8000-000000000001",
      "scheduled_for": "2026-11-16T00:00:00Z",
      "search_status": "QUEUED",
      "search_error": "example",
      "result_count": 1,
      "started_at": "2026-11-16T00:00:00Z",
      "finished_at": "2026-11-16T00:00:00Z",
      "notify_status": "WAITING",
      "notify_error": "example",
      "notified_at": "2026-11-16T00:00:00Z",
      "seen": false
    }
  ]
}
```


### ScheduleRunResponse

구현: `dait/schemas/schedule_run.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | 추가 JSON Schema 제약 없음 | id |
| schedule_id | string \| null | Y | "없음" | 추가 JSON Schema 제약 없음 | schedule_id |
| scheduled_for | string (date-time) | Y | "없음" | {"value.format": "date-time"} | scheduled_for |
| search_status | SearchStatus | Y | "없음" | {"value.reference": "SearchStatus", "value.enum": ["QUEUED", "RUNNING", "SUCCEEDED", "NO_RESULTS", "FAILED"]} | search_status |
| search_error | string \| null | Y | "없음" | 추가 JSON Schema 제약 없음 | search_error |
| result_count | integer \| null | Y | "없음" | 추가 JSON Schema 제약 없음 | result_count |
| started_at | string (date-time) \| null | Y | "없음" | {"value.anyOf0.format": "date-time"} | started_at |
| finished_at | string (date-time) \| null | Y | "없음" | {"value.anyOf0.format": "date-time"} | finished_at |
| notify_status | NotifyStatus | Y | "없음" | {"value.reference": "NotifyStatus", "value.enum": ["WAITING", "PENDING", "SENDING", "SENT", "FAILED", "UNKNOWN", "SKIPPED", "NOT_CONFIGURED"]} | notify_status |
| notify_error | string \| null | Y | "없음" | 추가 JSON Schema 제약 없음 | notify_error |
| notified_at | string (date-time) \| null | Y | "없음" | {"value.anyOf0.format": "date-time"} | notified_at |
| seen | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | seen |
| items | list[ScheduleRunItem] | N | "생성기" | {"value[].reference": "ScheduleRunItem"} | items |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "schedule_id": "00000000-0000-4000-8000-000000000001",
  "scheduled_for": "2026-11-16T00:00:00Z",
  "search_status": "QUEUED",
  "search_error": "example",
  "result_count": 1,
  "started_at": "2026-11-16T00:00:00Z",
  "finished_at": "2026-11-16T00:00:00Z",
  "notify_status": "WAITING",
  "notify_error": "example",
  "notified_at": "2026-11-16T00:00:00Z",
  "seen": false
}
```


### ScheduleUpdateRequest

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| local_time | string \| null | N | null | {"value.anyOf0.maxLength": 5, "value.anyOf0.minLength": 4, "validator": "값이 null이 아니면 HH:mm 24시간 형식; 00:00~23:59"} | local_time |
| timezone | string \| null | N | null | {"value.anyOf0.maxLength": 64, "value.anyOf0.minLength": 1, "service": "서비스에서 유효한 IANA 시간대 검사"} | timezone |
| enabled | boolean \| null | N | null | 추가 JSON Schema 제약 없음 | enabled |
| criteria | ScheduleCriteria \| null | N | null | {"value.anyOf0.reference": "ScheduleCriteria"} | criteria |

```json
{
  "local_time": "09:00"
}
```


모델 검증: 모든 필드가 null인 빈 변경은 422로 거부한다. 필드별 선택 가능 여부와 요청 전체의 유효성은 별개다.


### SessionResponse

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| authenticated | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | authenticated |
| user | UserPublic \| null | N | null | {"value.anyOf0.reference": "UserPublic"} | user |
| interests | list[InterestItem] | N | "생성기" | {"value[].reference": "InterestItem"} | interests |

```json
{
  "authenticated": false,
  "interests": [
    {
      "code": "ai.models",
      "name": "example",
      "group": "example"
    }
  ]
}
```


### SettingsResponse

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| default_count | enum(5, 10) | Y | "없음" | {"value.enum": [5, 10]} | default_count |
| keywords | list[string] | Y | "없음" | {"value.maxItems": 20, "value[].maxLength": 50, "value[].minLength": 1} | keywords |
| source_ids | list[string] | Y | "없음" | {"value.maxItems": 50, "value[].maxLength": 64, "value[].minLength": 1} | source_ids |
| categories | list[NewsCategory] | Y | "없음" | {"value.maxItems": 10, "value[].reference": "NewsCategory", "value[].enum": ["AI", "WEATHER", "ECONOMY", "POLITICS"]} | categories |
| in_app_notice | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | in_app_notice |
| email_notice | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | email_notice |
| updated_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | updated_at |

```json
{
  "default_count": 5,
  "keywords": [
    "example_"
  ],
  "source_ids": [
    "example_"
  ],
  "categories": [
    "AI"
  ],
  "in_app_notice": false,
  "email_notice": false,
  "updated_at": "2026-11-16T00:00:00Z"
}
```


### SettingsUpdateRequest

구현: `dait/schemas/settings.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| default_count | enum(5, 10) \| null | N | null | {"value.anyOf0.enum": [5, 10]} | default_count |
| keywords | list[string] \| null | N | null | {"value.anyOf0.maxItems": 20, "value.anyOf0[].maxLength": 50} | keywords |
| source_ids | list[string] \| null | N | null | {"value.anyOf0.maxItems": 50, "value.anyOf0[].maxLength": 64, "value.anyOf0[].minLength": 1} | source_ids |
| categories | list[NewsCategory] \| null | N | null | {"value.anyOf0.maxItems": 10, "value.anyOf0[].reference": "NewsCategory", "value.anyOf0[].enum": ["AI", "WEATHER", "ECONOMY", "POLITICS"]} | categories |
| in_app_notice | boolean \| null | N | null | 추가 JSON Schema 제약 없음 | in_app_notice |
| email_notice | boolean \| null | N | null | 추가 JSON Schema 제약 없음 | email_notice |

```json
{}
```


### SignupRequest

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| email | string (email) | Y | "없음" | {"value.format": "email"} | email |
| nickname | string \| null | N | null | {"value.anyOf0.maxLength": 30, "value.anyOf0.minLength": 2} | nickname |
| password | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 8} | 비밀번호 (8~128자) |
| password_confirm | string (password) | Y | "없음" | {"value.format": "password", "value.maxLength": 128, "value.minLength": 8} | password_confirm |
| terms_accepted | boolean \| null | N | null | 추가 JSON Schema 제약 없음 | terms_accepted |
| interests | list[InterestCode] | N | "생성기" | {"value.maxItems": 30, "value[].reference": "InterestCode", "value[].enum": ["ai.models", "ai.agents", "ai.devtools", "ai.opensource", "ai.infra", "economy.industry", "economy.business", "economy.startups", "economy.markets", "economy.jobs", "society.policy", "society.education", "society.health", "society.climate", "society.culture", "en.ai.models", "en.ai.agents", "en.ai.devtools", "en.ai.opensource", "en.ai.infra", "en.economy.industry", "en.economy.business", "en.economy.startups", "en.economy.markets", "en.economy.jobs", "en.society.policy", "en.society.education", "en.society.health", "en.society.climate", "en.society.culture"]} | interests |

```json
{
  "email": "reader@example.com",
  "nickname": "news_reader",
  "password": "Demo!S7ecure2026$",
  "password_confirm": "Demo!S7ecure2026$",
  "interests": [
    "ai.models"
  ]
}
```


### SourceInfo

구현: `dait/schemas/news.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| original_url | string | Y | "없음" | {"value.maxLength": 2000, "value.minLength": 1} | original_url |
| url_verified | boolean | Y | "없음" | 추가 JSON Schema 제약 없음 | url_verified |
| source_type | string | Y | "없음" | {"value.maxLength": 20, "value.minLength": 1} | source_type |

```json
{
  "original_url": "https://example.com/news/1",
  "url_verified": false,
  "source_type": "example_"
}
```


### TickRequest

구현: `dait/schemas/schedule_run.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| now | string (date-time) \| null | N | null | {"value.anyOf0.format": "date-time"} | now |

```json
{}
```


### TickResponse

구현: `dait/schemas/schedule_run.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| status | string | N | "ok" | 추가 JSON Schema 제약 없음 | status |
| tick_at | string (date-time) | Y | "없음" | {"value.format": "date-time"} | tick_at |
| due_schedules | integer | Y | "없음" | 추가 JSON Schema 제약 없음 | due_schedules |
| jobs_created | integer | Y | "없음" | 추가 JSON Schema 제약 없음 | jobs_created |
| jobs_skipped | integer | Y | "없음" | 추가 JSON Schema 제약 없음 | jobs_skipped |
| notifications_created | integer | N | 0 | 추가 JSON Schema 제약 없음 | notifications_created |

```json
{
  "tick_at": "2026-11-16T00:00:00Z",
  "due_schedules": 1,
  "jobs_created": 1,
  "jobs_skipped": 1
}
```


### TokenPair

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| access_token | string | Y | "없음" | 추가 JSON Schema 제약 없음 | access_token |
| refresh_token | string | Y | "없음" | 추가 JSON Schema 제약 없음 | refresh_token |
| token_type | 'bearer' | N | "bearer" | {"value.const": "bearer"} | token_type |

```json
{
  "access_token": "example",
  "refresh_token": "example_refresh_token_1234567890"
}
```


### UserPublic

구현: `dait/schemas/user.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| id | string | Y | "없음" | 추가 JSON Schema 제약 없음 | id |
| email | string | Y | "없음" | 추가 JSON Schema 제약 없음 | email |
| status | UserStatus | Y | "없음" | {"value.reference": "UserStatus", "value.enum": ["ACTIVE"]} | status |
| role | UserRole | Y | "없음" | {"value.reference": "UserRole", "value.enum": ["USER", "ADMIN"]} | role |
| nickname | string \| null | N | null | {"value.anyOf0.maxLength": 30, "value.anyOf0.minLength": 2} | nickname |

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "email": "reader@example.com",
  "status": "ACTIVE",
  "role": "USER",
  "nickname": "news_reader"
}
```


### WithdrawRequest

구현: `dait/schemas/auth.py`

| 필드 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| password | string (password) \| null | N | null | {"value.anyOf0.format": "password", "value.anyOf0.maxLength": 128, "value.anyOf0.minLength": 1} | password |
| confirm_text | '탈퇴' \| null | N | null | {"value.anyOf0.const": "탈퇴"} | confirm_text |

```json
{
  "confirm_text": "탈퇴"
}
```


### 5.1 Enum·Literal·타입 별칭 사전

아래 정의는 모델 파일에서 직접 추출한 허용값·상한·검증 타입이다. 모델 필드 표의 참조 타입은 이 사전을 따른다.


#### interest.py 허용값

```python
MAX_INTERESTS = 30

class InterestCode(StrEnum):
    """선택할 수 있는 관심사 소주제. `대주제.소주제` 형식의 영문 고정 코드다."""

    AI_MODELS = "ai.models"
    AI_AGENTS = "ai.agents"
    AI_DEVTOOLS = "ai.devtools"
    AI_OPENSOURCE = "ai.opensource"
    AI_INFRA = "ai.infra"
    ECONOMY_INDUSTRY = "economy.industry"
    ECONOMY_BUSINESS = "economy.business"
    ECONOMY_STARTUPS = "economy.startups"
    ECONOMY_MARKETS = "economy.markets"
    ECONOMY_JOBS = "economy.jobs"
    SOCIETY_POLICY = "society.policy"
    SOCIETY_EDUCATION = "society.education"
    SOCIETY_HEALTH = "society.health"
    SOCIETY_CLIMATE = "society.climate"
    SOCIETY_CULTURE = "society.culture"
    EN_AI_MODELS = "en.ai.models"
    EN_AI_AGENTS = "en.ai.agents"
    EN_AI_DEVTOOLS = "en.ai.devtools"
    EN_AI_OPENSOURCE = "en.ai.opensource"
    EN_AI_INFRA = "en.ai.infra"
    EN_ECONOMY_INDUSTRY = "en.economy.industry"
    EN_ECONOMY_BUSINESS = "en.economy.business"
    EN_ECONOMY_STARTUPS = "en.economy.startups"
    EN_ECONOMY_MARKETS = "en.economy.markets"
    EN_ECONOMY_JOBS = "en.economy.jobs"
    EN_SOCIETY_POLICY = "en.society.policy"
    EN_SOCIETY_EDUCATION = "en.society.education"
    EN_SOCIETY_HEALTH = "en.society.health"
    EN_SOCIETY_CLIMATE = "en.society.climate"
    EN_SOCIETY_CULTURE = "en.society.culture"
```


#### news.py 허용값

```python
MAX_SUMMARY_LINES = 3

MAX_TITLE_LENGTH = 500

MAX_RELATED = 10

class NewsCategory(StrEnum):
    """카테고리 Enum. WEATHER는 아직 수집·노출하지 않는다."""

    AI = "AI"
    WEATHER = "WEATHER"
    ECONOMY = "ECONOMY"
    POLITICS = "POLITICS"

ACTIVE_CATEGORIES: frozenset[NewsCategory] = frozenset(
    {NewsCategory.AI, NewsCategory.ECONOMY, NewsCategory.POLITICS}
)

class ContentStatus(StrEnum):
    """content_results.status 값. API의 processing_status로 변환해 노출한다."""

    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    TRANSLATED = "TRANSLATED"
    SUMMARIZED = "SUMMARIZED"
    READY = "READY"
    INSUFFICIENT = "INSUFFICIENT"
    FAILED = "FAILED"

PUBLIC_STATUSES: frozenset[ContentStatus] = frozenset(
    {ContentStatus.READY, ContentStatus.INSUFFICIENT}
)

ProcessingStatus = Literal["READY", "INSUFFICIENT", "FAILED", "PENDING"]

SortOrder = Literal["rank", "latest"]
```


#### nickname.py 허용값

```python
Nickname = Annotated[str, Field(min_length=2, max_length=30), BeforeValidator(normalize_nickname)]
```


#### user.py 허용값

```python
class UserStatus(StrEnum):
    """계정 상태. 지금은 정상 계정만 있다."""

    ACTIVE = "ACTIVE"

class UserRole(StrEnum):
    """역할. 모든 보호 라우트는 기본 거부이고 이 값으로 허용 범위를 정한다."""

    USER = "USER"
    ADMIN = "ADMIN"
```


#### schedule_run.py 허용값

```python
class SearchStatus(StrEnum):
    """검색 단계 상태. 결과 없음과 실패를 구분한다."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    NO_RESULTS = "NO_RESULTS"
    FAILED = "FAILED"

class NotifyStatus(StrEnum):
    """카카오(나에게 보내기) 전송 단계 상태. 검색 상태와 따로 기록한다."""

    WAITING = "WAITING"  # 검색이 끝나기 전
    PENDING = "PENDING"  # 보낼 차례
    SENDING = "SENDING"  # 한 서버가 보내는 중(lease)
    SENT = "SENT"
    FAILED = "FAILED"  # 재시도 대상
    UNKNOWN = "UNKNOWN"  # 응답이 끊겨 전송 여부를 모름 → 자동 재호출하지 않음
    SKIPPED = "SKIPPED"  # 결과 없음 등 보낼 필요 없음
    NOT_CONFIGURED = "NOT_CONFIGURED"
```


#### social.py 허용값

```python
class SocialProvider(StrEnum):
    """지원하는 소셜 공급자. DB CHECK 제약과 같은 값만 둔다."""

    GOOGLE = "GOOGLE"
```


#### settings.py 허용값

```python
MAX_KEYWORDS = 20

MAX_KEYWORD_LENGTH = 50

MAX_SOURCE_IDS = 50

MAX_SCHEDULES = 10

Keyword = Annotated[str, Field(min_length=1, max_length=MAX_KEYWORD_LENGTH)]

SourceId = Annotated[str, Field(min_length=1, max_length=64)]
```


## 6. 중첩 Pydantic 모델 코드

아래는 실제 소스에서 추출한 클래스 정의다. 연관 import·Enum·타입 별칭은 해당 파일을 따른다. 문서용으로 임의의 모델을 실제 구현처럼 만들지 않는다. AuthResponse는 UserPublic·TokenPair·InterestItem, NewsListResponse는 NewsListItem·PageInfo·NewsListMeta, ScheduleCreateRequest는 ScheduleCriteria를 중첩한다.


### auth.py

```python
class SignupRequest(BaseModel):
    """회원가입 요청. 알 수 없는 필드는 거부한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: EmailStr
    nickname: Nickname | None = None
    # SecretStr: 실수로 로그·repr에 찍혀도 *** 로만 보이게 한다.
    password: SecretStr = Field(min_length=8, max_length=128, description=_LENGTH_HINT)
    password_confirm: SecretStr = Field(min_length=8, max_length=128)
    # 기존 클라이언트 요청은 호환하되 가입 조건으로 사용하지 않는다.
    terms_accepted: bool | None = None
    # 선택 필드: 보내지 않으면 관심사 없이 가입한다(관심사 기능이 빠져도 가입 요청은 그대로 통한다).
    interests: list[InterestCode] = Field(default_factory=empty_interests, max_length=MAX_INTERESTS)

    @field_validator("nickname", mode="before")
    @classmethod
    # 입력: 회원가입 요청의 닉네임 원본 값.
    # 출력: 빈 문자열이면 None, 아니면 원본 값.
    # 동작: 선택하지 않은 닉네임을 공개 모델의 없음 값으로 통일한다.
    def _empty_nickname(cls, value: object) -> object:
        """빈 닉네임 입력을 없음 값으로 바꾼다.

        입력: value (회원가입 요청의 닉네임 원본 값)
        출력: object (빈 문자열이면 None, 아니면 원본 값)
        기능: 선택하지 않은 닉네임을 공개 모델의 없음 값으로 통일한다.
        """
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("interests")
    @classmethod
    # 입력: 회원가입 요청에서 검증된 관심사 코드 목록.
    # 출력: 중복이 없는 같은 관심사 코드 목록.
    # 동작: 같은 관심사를 두 번 선택한 요청을 거부한다.
    def _no_duplicate_interests(cls, value: list[InterestCode]) -> list[InterestCode]:
        """가입 시 보낸 관심사에 중복이 없는지 확인한다.

        입력: value (관심사 코드 목록)
        출력: 같은 목록
        기능: 중복이면 ValueError (422).
        """
        return check_no_duplicates(value)

    @field_validator("email")
    @classmethod
    # 입력: 형식 검증을 통과한 이메일.
    # 출력: 길이 제한을 통과한 같은 이메일.
    # 동작: 저장 가능한 최대 길이 254자를 넘는 이메일을 거부한다.
    def _check_email_length(cls, value: str) -> str:
        """이메일이 254자를 넘지 않는지 확인한다.

        입력: value (형식 검증을 통과한 이메일)
        출력: 같은 이메일
        기능: 254자를 넘으면 ValueError (UT-AUTH-002 경계).
        """
        if len(value) > _EMAIL_MAX_LENGTH:
            raise ValueError(_EMAIL_TOO_LONG)
        return value

    @model_validator(mode="after")
    # 입력: 비밀번호와 비밀번호 확인이 검증된 회원가입 모델.
    # 출력: 두 값이 일치하는 같은 회원가입 모델.
    # 동작: 상수 시간 비교로 비밀번호 확인 불일치를 거부한다.
    def _check_password_confirmation(self) -> Self:
        """비밀번호 확인이 일치하는지 검사한다.

        입력: 없음(이미 검증된 필드들)
        출력: self
        기능: 두 비밀번호가 다르면 ValueError. 비교는 상수 시간으로 한다.
        """
        same = hmac.compare_digest(
            self.password.get_secret_value().encode(),
            self.password_confirm.get_secret_value().encode(),
        )
        if not same:
            raise ValueError(_MISMATCH)
        return self

class TokenPair(BaseModel):
    """발급된 토큰 한 쌍. 원문은 이 응답에서만 볼 수 있다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"

class AuthResponse(BaseModel):
    """가입·로그인 응답: 사용자 정보, 토큰, 저장된 관심사."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user: UserPublic
    tokens: TokenPair
    onboarding_required: bool = False
    # 메인 화면이 로그인 직후 바로 쓰도록 DB의 관심사를 함께 내려준다(없으면 빈 목록).
    interests: list[InterestItem] = Field(default_factory=empty_items)

class WithdrawRequest(BaseModel):
    """회원탈퇴 요청. 비밀번호 계정은 비밀번호를, 구글 전용 계정은 확인 문구를 받는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    password: SecretStr | None = Field(default=None, min_length=1, max_length=128)
    confirm_text: Literal["탈퇴"] | None = None
```


### user.py

```python
class UserPublic(BaseModel):
    """응답에 내보내는 사용자 정보. 해시 같은 내부 값은 없다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    email: str
    status: UserStatus
    role: UserRole
    nickname: Nickname | None = None
```


### interest.py

```python
class InterestItem(BaseModel):
    """화면에 보여 줄 관심사 한 개: 저장 코드, 한글 이름, 대주제."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: InterestCode
    name: str
    group: str
```


### news.py

```python
class NewsListItem(BaseModel):
    """목록 카드 한 건. 화면의 rank·제목·출처·시각·요약·상태·원문에 대응한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    original_language: str = "und"
    author_name: str | None = None
    rank: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    source_name: str = Field(min_length=1, max_length=200)
    published_at: datetime
    category: NewsCategory
    summary_lines: list[Annotated[str, Field(max_length=500)]] = Field(max_length=MAX_SUMMARY_LINES)
    processing_status: ProcessingStatus
    original_url: str = Field(min_length=1, max_length=2000)
    is_partial: bool

    @field_validator("original_url")
    @classmethod
    def _https_only(cls, value: str) -> str:
        """원문 URL은 검증된 HTTPS만 허용한다.

        입력: value (저장된 canonical_url)
        출력: 같은 문자열
        기능: http·기타 scheme이면 ValueError로 응답 생성을 막는다.
        """
        if not value.startswith("https://"):
            raise ValueError(_HTTPS_ONLY)
        return value

class PageInfo(BaseModel):
    """커서 페이지네이션 메타."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    next_cursor: str | None = Field(default=None, max_length=500)
    has_more: bool

class NewsListMeta(BaseModel):
    """목록 부가 정보: 부분 실패 여부와 랭킹 기준 설명."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_visible: int = Field(ge=0)
    partial: bool
    message: str | None = Field(default=None, max_length=200)
    rank_basis: list[str] = Field(max_length=10)

class NewsListResponse(BaseModel):
    """GET /v1/news 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[NewsListItem] = Field(max_length=50)
    page: PageInfo
    meta: NewsListMeta
```


### settings.py

```python
class ScheduleCriteria(BaseModel):
    """예약에 저장하는 관심 조건. settings의 관심 조건과 같은 검증을 거친다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: list[Keyword] = Field(default_factory=list, max_length=MAX_KEYWORDS)
    source_ids: list[SourceId] = Field(default_factory=list, max_length=MAX_SOURCE_IDS)
    categories: list[NewsCategory] = Field(min_length=1, max_length=10)
    # None이면 검색 시점에 예약 소유자의 저장 관심사(user_interests)를 따른다.
    # 명시적 목록(빈 목록 포함)은 그 스냅샷만 쓰고, []는 관심사 검색을 끈다.
    interests: list[InterestCode] | None = Field(default=None, max_length=MAX_INTERESTS)

    @field_validator("keywords")
    @classmethod
    def _check_keywords(cls, value: list[str]) -> list[str]:
        for item in value:
            if _CONTROL_CHARS.search(item):
                raise ValueError(_BAD_KEYWORD)
        return value

    @field_validator("categories")
    @classmethod
    def _check_categories(cls, value: list[NewsCategory]) -> list[NewsCategory]:
        inactive = [c for c in value if c not in ACTIVE_CATEGORIES]
        if inactive:
            raise ValueError(_INACTIVE_CATEGORY)
        return value

class ScheduleResponse(BaseModel):
    """예약 한 건의 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(min_length=1, max_length=64)
    enabled: bool
    criteria: ScheduleCriteria
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ScheduleCreateRequest(BaseModel):
    """POST /v1/me/schedules 요청."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_time: str = Field(min_length=4, max_length=5)
    timezone: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    criteria: ScheduleCriteria

    @field_validator("local_time")
    @classmethod
    def _check_time(cls, value: str) -> str:
        """HH:mm 24시간 형식인지 확인한다."""
        if not _TIME_PATTERN.fullmatch(value):
            raise ValueError(_BAD_TIME)
        return value
```


## 7. 화면 액션·API·피드백
| 화면/액션 | 호출 | 완료·실패 안내 |
|---|---|---|
| 메인 검색·조건 초기화 | GET /v1/news?q=... | 로딩 → 목록/빈 결과/부분 지연/오류·재시도 |
| 관심사·국내 칩 | GET /v1/news 및 GET /v1/news/activity | 선택 강조·건수 갱신, 실패 시 기존 화면 유지 |
| 스크롤·계속 읽기 | GET /v1/news?cursor=... | 로그인 사용자 추가 페이지 이어 붙이기 |
| 원문 클릭 | 응답 original_url + PUT /v1/news/{id}/read | 새 탭·읽음 표시, 기록 실패는 원문 접근을 막지 않음 |
| 링크 복사 | Clipboard API, 별도 서버 API 없음 | 복사 완료 또는 실패 안내 |
| 관심사 선택·해제 | PUT /v1/me/interests | 자동 저장 중·완료·실패, 다시 저장 |
| 예약 추가·삭제 | POST /v1/me/schedules; DELETE /v1/me/schedules/{id} | 예약칩·건수 갱신, 입력 오류·외부 등록 실패 안내 |
| 닉네임 저장 | PATCH /v1/me/nickname | 완료·중복·검증 실패 안내 |
| 인증·탈퇴 | 4절 인증·계정 API | 가입 후 로그인 팝업, 로그인 후 온보딩 분기, 탈퇴 후 토큰 제거 |

## 8. 필수 항목 검토 결과
| 가이드 항목 | 반영 위치 | 검토 |
|---|---|---|
| URL·Method | 3~4절 | 현재 라우트 전체 추출, include_in_schema=False 내부 경로 포함 |
| 모델·필수/선택·타입·예시 | 4~5절 | 실제 Pydantic 계약과 예시 검증 |
| nested Pydantic | 6절 | 실제 중첩 클래스 코드 포함 |
| 표준 오류·상세 정보 | 2절·4절 | 실제 3필드 오류와 발생조건 명시; 응답 details 미구현은 한계로 공개 |
| 4xx·5xx | 2.3절·4절 | 재시도·입력 수정·인증·복구 규칙 구분 |
| 화면 설계 연결 | 7절 | 현재 UI 제공 여부와 API 유지 계약 구분 |

API 계약 목록은 소스 AST와 대조했고, 모델 예시는 실제 Pydantic 모델로 검증했다. 운영 호출·장애 유발 테스트는 하지 않았다. 오류 details 필드 추가는 서버 변경이 필요하므로 이번 문서 수정만으로 구현됐다고 주장하지 않는다.
