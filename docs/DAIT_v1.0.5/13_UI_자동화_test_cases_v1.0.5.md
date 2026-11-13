# DAIT UI 자동화 테스트 케이스

## English Metadata

| 항목 | 값 |
|---|---|
| English Title | DAIT UI Automation Test Cases |
| Search Keywords | DAIT, UI automation test cases, Playwright, pytest, browser automation, E2E, main screen, detail dialog, settings screen, auth popup, category filter, sorting, schedule runs |
| English Summary | Browser UI automation test cases for the DAIT stage-1 MVP main, detail, and settings screens using Playwright for Python and pytest. Covers the immediate auth progress popup, category filters (AI/economy/politics), ranking/latest sorting, search, pagination, read status, schedule CRUD, and schedule-run result UI against the current static SPA frontend. |

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.5 |
| 기준일 | 2026-11-13 |
| 대상 | DAIT 단계 1 MVP 메인·설정 UI |
| 테스트 수준 | Browser UI Automation / End-to-End |
| 기본 도구 | Playwright for Python, pytest |
| 기준 문서 | 화면·기능·API·DB·통합 테스트 문서 v1.0.4 |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | 문서 세트 버전 1.0.2로 갱신 |
| 1.0.3 | seonghoon.yang | 2026-11-12 | 신규 프론트엔드(index.html/app.js/news-ui.js/settings-ui.js) 기준 UI 자동화 케이스 갱신 |
| 1.0.4 | seonghoon.yang | 2026-11-13 | v1.0.4 UI 반영 — 국내/해외 지역 칩, 관심사 칩·집계, member-only 게이팅, 출처 태그·기자명, 페이지 버튼 문구 |
| 1.0.4.1 | seonghoon.yang | 2026-11-13 | 상세보기 화면·설정 `노출·알림` 메뉴 UI 제거 반영 — 상세·노출·알림 UI 케이스 폐기/API 수준 전환 |
| 1.0.5 | seonghoon.yang | 2026-11-13 | 영문 기사 기능 중단 반영 — 해외 칩·출처 태그·영문 관심사 UI 케이스 폐기, 국내 칩만 유지 |

## 0.1 v1.0.3 프론트엔드 기준

- 화면: `src/frontend/public/index.html`(메인 목록), `settings.html`(설정).
  (1.0.4.1: 상세 `<dialog>`와 설정 `노출·알림` 섹션은 UI에서 제거 — `#display` 해시는 `#schedule`로 리다이렉트)
- 스크립트: `app.js`(인증 다이얼로그·목록·검색), `news-ui.js`, `settings-ui.js`.
- v1.0.3 동작: 로그인·가입 **제출 즉시** 진행 팝업 표시, 응답 완료 시 자동 닫힘.
- 카테고리 필터(AI·경제·정치), 랭킹/최신 정렬, 검색, 페이지네이션, 읽음 표시,
  예약 생성·수정·삭제, 예약 검색 결과(`schedule-runs`) 확인 UI를 대상으로 한다.
- v1.0.4 추가: 로그인 사용자에게 관심사 집계 칩
  (최대 5개 + `더 보기`), 카드의 기자명 표시, 비로그인 member-only 영역 숨김,
  페이지 버튼 `이전/다음 페이지` 문구.
- v1.0.5: 해외 지역 칩·`해외`/`구분 미확인` 출처 태그·영문 관심사 칩 제거 —
  한국어 기사만 노출, `국내` 칩만 존재.

## 1. 목적

사용자가 브라우저에서 수행하는 핵심 흐름을 자동 검증한다. 테스트는 화면 표시만 확인하지 않고 UI 조작, API 요청, 저장 결과, 재진입 복원, 오류 복구와 접근성 계약을 함께 확인한다.

## 2. 범위

### 2.1 포함

- 메인: 뉴스 목록, 카테고리, 정렬, 검색, 빈 결과, 부분 상태, 재시도, 원문 열기·링크 복사 (상세보기 화면 미제공 — 1.0.4.1)
- ~~상세보기~~ (폐기 — API 수준으로만 검증, 1.0.4.1)
- 설정: 예약 수집, 관심 설정, 닉네임·계정 관리, 저장, 재진입 복원. `노출·알림` 섹션은 화면에 없다(1.0.4.1 — API 수준).
- 공통: 네비게이션, 반응형 레이아웃, 키보드 조작, 접근성 이름, 로딩·오류 상태
- 인증 경계: 비인증 상태의 보호 화면 접근 차단

### 2.2 제외

- 실제 공개 뉴스 사이트, 실제 LLM, 실제 SMTP 호출
- 서버 내부 랭킹 가중치와 LLM 요약 품질의 정성 평가
- 현재 화면설계서에 세부 UI가 없는 소셜 공급자별 로그인 화면
- 정적 목업의 검색·저장 버튼 실동작. 기능 자동화는 실제 앱 환경에서 수행한다.

## 3. 참조 문서

| 문서 | 적용 내용 |
|---|---|
| `04_기능별상세설계서_v1.0.5.md` | FR, 화면 상태, 권한·검증 |
| `05_상세기획서_v1.0.5.md` | 사용자 흐름, 예외, 검수 기준 |
| `06_API_설계서_v1.0.5.md` | UI가 호출하는 `/v1` API 계약 |
| `10_통합_test_cases_v1.0.5.md` | 통합 시나리오와 seed |
| `11_통합_test_procedure_v1.0.5.md` | 통합 환경, 장애·보안 절차 |
| `12_test_guide_v1.0.5.md` | 실행 순서와 품질 게이트 |
| `DAIT_화면설계서_v1.0.5.pptx` | 메인·설정 화면 구성과 표시 우선순위 |
| `mockup/index.html`, `mockup/settings.html` | 메인·설정 DOM과 반응형 기준 |

## 4. 공통 사전 조건

1. 격리된 UI 테스트 DB와 Redis를 사용한다.
2. USER-A는 인증된 사용자이며 기본 설정과 `08:30 Asia/Seoul` 예약을 가진다.
3. USER-B는 소유권 검증용 별도 사용자이다.
4. READY 3건, INSUFFICIENT 1건, FAILED 1건의 결정적 seed를 사용한다.
5. 승인 출처는 OpenAI, Anthropic을 포함하고 모든 원문 URL은 HTTPS다.
6. 외부 주소, Clipboard, 오류 API는 Playwright route 또는 테스트 fake로 제어한다.

## 5. 실행 환경 매트릭스

| 프로젝트 | 뷰포트 | 주요 목적 |
|---|---:|---|
| Desktop Chromium | 1440×900 | 기본 회귀, 스크린샷, 2열 레이아웃 |
| Mobile Chromium | 390×844 | 단일 열, 하단 탐색, 가로 넘침, 44px 터치 대상 |

Firefox·WebKit은 호환성 게이트로 추가할 수 있지만 v1.0.4 기본 회귀는 Chromium으로 고정한다.

## 6. 케이스 ID 규칙

`UI-<기능군>-<3자리 순번>`을 사용한다.

| 기능군 | 의미 |
|---|---|
| COM | 공통·반응형·접근성 |
| AUTH | 인증 경계 |
| HOME | 메인·목록·검색 |
| DETAIL | 뉴스 상세 |
| SET | 설정·예약 |
| STATE | 로딩·빈 상태·오류 복구 |

## 7. 공통·인증 케이스

| ID | 우선순위 | 관련 요구 | 시나리오·절차 | 기대 결과 | 증거 |
|---|---|---|---|---|---|
| UI-COM-001 | P0 | 공통, FR-HOME-01 | Desktop 메인 진입 후 랜드마크, 탐색, `h1`, 검색, 뉴스 목록을 role로 조회한다. | 핵심 영역이 중복 없이 보이고 현재 화면이 탐색에서 식별된다. | screenshot |
| UI-COM-002 | P0 | 공통 반응형 | 메인과 설정을 Desktop·Mobile로 열고 `scrollWidth <= clientWidth`를 확인한다. | 가로 넘침·겹침이 없고 Mobile은 단일 열과 두 메뉴 하단 탐색을 사용한다. | 4 screenshots |
| UI-COM-003 | P1 | 공통 접근성 | `Tab`으로 해당 화면의 모든 조작 요소를 순회하고 focus-visible을 확인한다. | 포커스가 유실·고립되지 않고 버튼·링크·입력의 이름이 유일하다. | trace, screenshot |
| UI-COM-004 | P1 | FR-HOME-02, AC-STATE-01 | `aria-live="polite"` 영역에 로딩·빈 결과·오류 메시지를 순차적으로 노출한다. | 상태 변경이 텍스트로 전달되고 새로 추가된 메시지가 포커스를 빼앗지 않는다. | DOM assertion |
| UI-AUTH-001 | P0 | FR-AUTH-03 | 인증 상태를 제거하고 설정 URL을 직접 연다. | 로그인 화면으로 이동하거나 정책상 일반화된 인증 오류를 표시하며 설정 데이터는 보이지 않는다. | URL, screenshot |
| UI-AUTH-002 | P0 | FR-AUTH-03 | USER-A 저장 상태로 설정에 진입한 후 세션을 만료시키고 저장을 시도한다. | 저장 성공을 표시하지 않고 재인증 흐름으로 전환한다. | network, screenshot |

## 8. 메인·검색 케이스

| ID | 우선순위 | 관련 요구 | 시나리오·절차 | 기대 결과 | 증거 |
|---|---|---|---|---|---|
| UI-HOME-001 | P0 | FR-HOME-01, IT-HOME-001 | 메인을 열고 `GET /v1/news` 응답과 카드를 비교한다. | READY·INSUFFICIENT 카드만 보이며 제목, 출처, 발행 시각, 카테고리, 요약, 상태, 행동이 API와 일치한다. | response, screenshot |
| UI-HOME-002 | P0 | FR-HOME-01, IT-HOME-003 | `랭킹순`을 선택한다. | 카드 순서와 1~N 순위가 API `sort=rank`와 일치한다. | request, DOM order |
| UI-HOME-003 | P0 | FR-HOME-01, IT-HOME-004 | `최신순`을 선택한다. | `sort=latest`가 전송되고 발행 시각 역순으로 재배치된다. | request, DOM order |
| UI-HOME-004 | P0 | FR-SEARCH-01, IT-HOME-005~006 | 제목 키워드와 요약 전용 키워드를 각각 검색한다. | 검색어가 trim되고 각 키워드의 대상 기사만 보인다. | request, cards |
| UI-HOME-005 | P0 | FR-SEARCH-01, IT-HOME-007 | 0건 검색어 입력 후 초기화한다. | 빈 결과 안내와 초기화 행동이 보이고 초기화 후 기본 목록이 복원된다. | screenshot, request count |
| UI-HOME-006 | P1 | FR-HOME-01 | `전체`와 `AI·기술` 필터를 전환한다. | 선택 상태가 시각·ARIA 상태로 표시되고 API category와 일치한다. | DOM, request |
| UI-HOME-007 | ~~P1~~ | FR-HOME-01 | ~~카드의 `상세 보기`를 선택한다.~~ (폐기 — 1.0.4.1 상세 화면 제거, 카드 제목·`원문 열기`가 원문 직결) | — | — |
| UI-HOME-008 | P1 | FR-DETAIL-02 | 카드의 `원문 열기`를 선택한다. | 검증된 HTTPS URL이 새 탭에서 열리고 opener 격리 정책을 따른다. | popup URL |
| UI-HOME-009 | P1 | FR-HOME-02, IT-HOME-008 | partial 응답을 반환한다. | 정상 카드는 유지되고 일부 출처 지연이 색상과 텍스트로 함께 표시된다. | screenshot |
| UI-HOME-010 | ~~P0~~ | FR-SEARCH-01 (v1.0.4) | ~~로그인 상태에서 `국내`/`해외` 지역 칩을 각각 선택한다.~~ (폐기 — 1.0.5 해외 칩 제거) | — | — |
| UI-HOME-011 | P0 | FR-SEARCH-01 (v1.0.4) | 관심사를 저장한 사용자로 메인을 열고 관심사 칩을 확인·클릭한다. | 칩에 `interest_counts` 건수가 표시되고 클릭 시 `interest=<code>` 필터 목록이 나온다. 6개 이상이면 `더 보기` 토글이 동작한다. | request, DOM |
| UI-HOME-012 | P1 | FR-HOME-01 (v1.0.4) | 비로그인 상태로 메인을 연다. | 카테고리·관심사 탐색 영역이 숨겨지고 제한 목록(최신순)만 표시된다. | screenshot |
| UI-HOME-013 | P1 | FR-HOME-01 (v1.0.4) | 명시적 바이라인이 있는 기사 카드를 확인한다. | `author_name`(예: `홍길동 기자`)이 메타에 표시되고 없으면 표시되지 않는다. | DOM |

## 9. 상세보기 케이스 (1.0.4.1: 상세 화면 미제공 — 전 항목 폐기, API 수준 IT-DETAIL-*로 대체 검증)

| ID | 우선순위 | 관련 요구 | 시나리오·절차 | 기대 결과 | 증거 |
|---|---|---|---|---|---|
| UI-DETAIL-001 | P0 | FR-DETAIL-01, IT-DETAIL-001 | 메인 첫 카드에서 상세로 이동한다. | breadcrumb, 제목, 출처, 발행일이 목록·API와 일치한다. | response, screenshot |
| UI-DETAIL-002 | P0 | FR-DETAIL-01, AC-DETAIL-01 | AI 요약 목록을 조회한다. | 비어 있지 않은 요약 3줄이 정확히 보인다. | DOM count |
| UI-DETAIL-003 | P0 | FR-DETAIL-01, IT-DETAIL-002~003 | ~~번역·처리 정보·원본 정보를 조회한다.~~ (1.0.5: 번역 항목 폐기 — 처리 정보·원본 정보만) | 처리 시각·상태·버전, 출처·HTTPS URL·발행일이 API와 일치한다. | DOM, response |
| UI-DETAIL-004 | P1 | FR-DETAIL-01 | 관련 뉴스 항목을 선택한다. | 선택한 news ID의 상세로 이동하고 헤더·요약이 갱신된다. | URL, response |
| UI-DETAIL-005 | P0 | FR-DETAIL-02, AC-DETAIL-03 | `원문 새 탭`을 선택한다. | API가 제공한 HTTPS URL만 새 탭으로 열린다. | popup URL |
| UI-DETAIL-006 | P0 | FR-DETAIL-02, IT-DETAIL-007 | Clipboard 권한 허용 후 `링크 복사`를 선택한다. | 현재 뉴스의 canonical URL이 복사되고 성공 안내가 보인다. | clipboard value |
| UI-DETAIL-007 | P1 | FR-DETAIL-02 | Clipboard 권한을 차단하고 복사를 시도한다. | 대체 복사 또는 직접 선택 안내가 보이고 정상 콘텐츠는 유지된다. | screenshot |
| UI-DETAIL-008 | P1 | FR-DETAIL-01, IT-DETAIL-004~005 | 404와 INSUFFICIENT 응답을 각각 제공한다. | 404는 일반화된 안내와 복귀 행동, INSUFFICIENT는 제공 가능한 데이터와 부분 상태를 표시한다. | 2 screenshots |

## 10. 설정·예약 케이스

| ID | 우선순위 | 관련 요구 | 시나리오·절차 | 기대 결과 | 증거 |
|---|---|---|---|---|---|
| UI-SET-001 | P0 | FR-SET-01~03, IT-SET-001 | USER-A로 설정을 열고 settings·schedules 응답과 화면 필드를 비교한다. | `08:30`, `Asia/Seoul`, 관심 조건, 계정 정보가 일치하며 `노출·알림` 섹션·알림 토글은 표시되지 않는다(1.0.4.1). | responses, screenshot |
| UI-SET-002 | P0 | FR-SET-01, IT-SCH-001~002 | 예약을 `09:00 Asia/Seoul`로 생성 또는 변경하고 저장한다. | POST/PATCH가 1회 호출되고 다음 실행 시각이 새 값으로 표시된다. | request, response |
| UI-SET-003 | P0 | FR-SET-01, IT-SCH-003 | 예약 활성 스위치를 끄고 저장한다. | `enabled=false`가 전송되고 재조회·재진입 후에도 비활성이다. | request, reload |
| UI-SET-004 | P1 | FR-SET-01, IT-SCH-004 | 테스트 예약을 삭제하고 확인한다. | DELETE 204 후 목록에서 사라지고 재조회에서도 복원되지 않는다. | request, reload |
| UI-SET-005 | P0 | FR-SET-02, IT-SET-002 | 키워드에 공백·중복을 포함하고 승인 출처·AI 카테고리를 선택해 저장한다. | trim·중복 제거된 목록과 선택 ID 배열이 저장되고 화면에 복원된다. | request body, reload |
| UI-SET-006 | ~~P0~~ | FR-SET-03, IT-SET-004~006 | ~~기본 노출 수를 10→5로 바꾸고 저장한다.~~ (폐기 — `노출·알림` UI 제거, 1.0.4.1. `default_count`는 `PATCH /v1/me/settings` API로 검증) | — | — |
| UI-SET-007 | P0 | FR-SET-02~03, IT-SET-003 | 허용되지 않은 출처, 카테고리, 잘못된 시간을 각각 입력한다. | 항목별 오류가 입력과 연결되고 저장 API·DB는 변경되지 않는다. (노출 수 검증은 API 수준) | error DOM, request absence |
| UI-SET-008 | P0 | FR-SET-02~03, IT-SET-007 | 값을 바꾸고 `취소`를 선택한다. | PATCH/POST가 호출되지 않고 서버 최신 값으로 복원된다. | request count, DOM |
| UI-SET-009 | P0 | FR-SET-01~03 | 설정을 저장하고 새 페이지에서 재진입한다. | 저장 성공 안내 후 서버 값이 복원되며 클라이언트 메모리만으로 유지하지 않는다. | fresh context screenshot |
| UI-SET-010 | P1 | FR-SET-01~03 | 저장 API를 500으로 응답시킨다. | 성공으로 표시하지 않고 사용자 입력을 유지하며 재시도 행동을 제공한다. | trace, screenshot |

## 11. 상태·복구 케이스

| ID | 우선순위 | 관련 요구 | 시나리오·절차 | 기대 결과 | 증거 |
|---|---|---|---|---|---|
| UI-STATE-001 | P0 | FR-HOME-02 | 뉴스 API 응답을 지연시킨다. | 로딩 텍스트·상태가 즉시 보이고 응답 후 카드로 교체된다. | video, DOM |
| UI-STATE-002 | P0 | FR-HOME-02 | 뉴스 API를 500으로 응답한 후 재시도에서 200을 반환한다. | 일반화된 오류와 `다시 시도`가 보이고 재시도 후 목록이 복원된다. | trace, screenshot |
| UI-STATE-003 | P1 | FR-HOME-02 | 브라우저를 offline으로 전환하고 새로고침한다. | 네트워크 안내와 재시도가 보이며 온라인 복구 후 정상 조회된다. | video |
| UI-STATE-004 | P1 | 공통 | 중복 클릭·저장을 빠르게 2회 수행한다. | 중복 요청·중복 예약이 생성되지 않고 진행 중 상태가 표시된다. | request count |

## 12. 합격 기준

- P0 케이스는 100% PASS해야 한다.
- P1 케이스는 알려진 결함과 승인된 예외가 없으면 100% PASS해야 한다.
- 재시도 후에만 PASS한 케이스는 flaky로 기록하고 원인을 제거할 때까지 출시 게이트에서 제외하지 않는다.
- screenshot 비교는 동적 시각·ID·랜덤 값을 seed로 고정한 후 수행한다.
- 응답·trace·screenshot에 토큰, 비밀값, 개인정보를 남기지 않는다.

## 13. 추적성 요약

| 요구사항 | 대표 UI 케이스 |
|---|---|
| FR-AUTH-03 | UI-AUTH-001~002 |
| FR-HOME-01 | UI-HOME-001~003, UI-HOME-006~008 |
| FR-SEARCH-01 | UI-HOME-004~005 |
| FR-HOME-02 | UI-HOME-009, UI-STATE-001~003 |
| FR-DETAIL-01 | UI-DETAIL-001~004, UI-DETAIL-008 |
| FR-DETAIL-02 | UI-DETAIL-005~007 |
| FR-SET-01 | UI-SET-001~004 |
| FR-SET-02 | UI-SET-005, UI-SET-007~010 |
| FR-SET-03 | UI-SET-006~010 |
