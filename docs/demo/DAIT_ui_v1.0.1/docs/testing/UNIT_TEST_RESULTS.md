# 자동 단위 테스트 결과 (2026-11-09 / Asia/Seoul)

## 실행 결과

실제 C:/DAIT_test/DAIT_ui에서 Python 3.12.14 전용 환경으로 scripts/run_unit_tests.py를 실행했습니다. 사용자 기존 서비스 가상환경은 변경하지 않았습니다.

| 항목 | 결과 |
|---|---:|
| 자동 검사 | 118개 |
| 통과 | 106개 |
| 실패 | 12개 |
| 환경 오류 / skip / xfail | 0 / 0 / 0 |
| 정순·역순 결과 비교 | 118개 결과 동일 |
| Python 라인 커버리지 | 52.7% |
| Python 분기 커버리지 | 36.8% |
| Ruff 진단 | 45건 |
| Ruff 포맷 필요 | 30개 파일 |
| Pyright strict 오류 | 1,616건 |

최종 판정은 **문서 완료 기준 미충족**입니다. 테스트 환경 구축과 실행은 완료했지만 제품이 문서 전체를 만족한다는 뜻은 아닙니다. 순서 변경 1회에서도 같은 결과가 나왔으나 장기간 flaky 0을 보장하는 것은 아닙니다.

## 실패 12개 (문서 ID 9개)

| ID | 문서 기대 | 현재 동작 |
|---|---|---|
| UT-AUTH-001 | 가입 직후 최초 세션 생성 | 가입 후 별도 로그인 |
| UT-AUTH-002 | 이메일 형식 검증 | 자유 아이디 방식 (2개 입력 실패) |
| UT-SEARCH-007 | 검색어 100자 제한 | 200자 제한 |
| UT-SEARCH-002 | AI 요약문도 키워드 검색 | 제목·RSS 설명·한국어 제목 검색 |
| UT-LINK-002 | HTTP 원문 링크 거부 | HTTP/HTTPS 모두 허용 |
| UT-HOME-001 | READY 기사만 공개 목록 | 미생성·실패 상태 기사도 목록 표시 |
| UT-DETAIL-008 | NEWS_NOT_FOUND 코드 | 404와 일반 오류 메시지 |
| UT-AI-007 | 수치 변형 시 READY 금지 | 형식 검증만으로 수치 변형까지 차단하지 못함 |
| UT-COL-003 | 사설 IP 출처 요청 전 거부 | 수집 함수 자체의 사설 IP 사전 차단 없음 (3개 입력 실패) |

차이를 숨기려고 기대값을 바꾸거나 skip/xfail을 사용하지 않았습니다. 이메일/가입 정책·READY 공개 정책·검색 정책은 기존 사용자 요구와의 정합성을 먼저 결정해야 합니다. 이번 작업에서 이메일 인증 5단계나 업무 기능은 구현하지 않았습니다.

## 문서 추적 범위

139개 UT ID 전체를 목록화했습니다. FAIL 9, CHECKED_PARTIALLY 36, NOT_IMPLEMENTED 27, DESIGN_DIFFERENCE 26, NOT_COVERED 41입니다. CHECKED_PARTIALLY는 일부 기대결과만 검사했다는 뜻이며 PASS로 합산하지 않습니다. 118개 실행 케이스에는 파라미터 변형·기존 회귀·문서 밖 임베딩 검사도 포함되므로 UT ID 수와 다릅니다.

미구현은 예약·알림·관련 뉴스·Redis 캐시·refresh·회원탈퇴 등을 포함합니다. 설정 화면은 실제 저장 서비스와 구분했습니다. 브라우저 Clipboard/오프라인/CSS 터치 영역 및 기존 HTTP 통합 테스트 등은 이번 단위 실행에 포함하지 않았습니다.

## 격리와 변경 범위

실제 회원·기사·요약·번역·색인·대기열 DB 접근을 차단했습니다. 각 테스트가 자체 임시 DB를 사용하며 LLM·RSS는 mock/fake, 시각·UUID·토큰은 고정 fixture를 사용했습니다. 모델과 모델 런타임은 설치하지 않았습니다. Windows asyncio 내부 wakeup socketpair만 허용하고 애플리케이션 외부 연결·SMTP·프로세스 생성은 차단했습니다.

업무 소스 backend/frontend 33개 파일의 실행 전후 해시가 동일합니다. 기존 테스트 3개 파일에서는 Windows 임시 DB 연결 해제와 누락된 published_at fixture 열만 보완했습니다. 기존 HTTP 테스트·과거 JavaScript 테스트는 보존했습니다.

Ruff/Pyright 실패는 독립 품질 게이트 결과입니다. 동적 dict·미기재 타입 등 기존 코드와 테스트 타입 진단, 테스트 환경에서 의도적으로 설치하지 않은 모델 라이브러리 관련 진단도 포함되므로 오류 수 전체를 런타임 결함 수로 해석하지 않습니다. 실제 제품 코드를 변경해 진단을 억지로 제거하지 않았습니다.

## 증거와 재실행

- .tmp/test-results/REPORT.md: 자동 생성 요약과 추적표
- unit.xml / unit-reversed.xml / cases-baseline.json / cases-reversed.json: 실행 결과
- traceability.json: 전체 문서 ID별 검사 연결
- ruff-check.json / ruff-format.log / pyright.json: 품질 검사 증거
- .tmp/coverage/index.html: 커버리지 상세

재실행 방법은 [UNIT_TEST_GUIDE.md](UNIT_TEST_GUIDE.md)를 따릅니다. .tmp 및 가상환경은 Git 제외 대상입니다. 이 문서는 2026-11-09 실행 결과의 기록이며, 다음 실행 결과는 .tmp 보고서를 우선 확인합니다.
