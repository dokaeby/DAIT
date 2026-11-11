# 문서 기준 자동 단위 테스트

기준: test-cases-v1.0.1.md와 test-procedure-v1.0.1.md. 이번 작업은 테스트 환경과 검사 코드 구축이며 미구현 업무 기능을 구현하는 작업이 아닙니다.

## 반복 실행

프로젝트 루트 PowerShell에서 최초 한 번 준비합니다. 실제 서비스 .venv와 분리합니다.

~~~powershell
py -m venv .venv-test
.\.venv-test\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv-test\Scripts\python.exe -m pip install -e . --no-deps
.\.venv-test\Scripts\python.exe scripts\run_unit_tests.py
~~~

requirements-dev.lock.txt는 실제 검증에 사용한 Python 3.12.14 환경의 의존성 고정 목록입니다. AI/임베딩 모델과 sentence-transformers는 테스트 환경에 설치하지 않습니다. Pyright 실행에는 Node가 필요하며 설치된 Node가 없으면 도구의 Node 준비 과정이 필요할 수 있습니다.

이번 PC에서 제가 사용한 실행 파일은 C:/Users/Playdata/Documents/ChatGPT/다잇/.test-venv/Scripts/python.exe입니다. 위 .venv-test는 다른 PC에서도 동일 절차로 다시 구성하기 위한 경로입니다.

실패가 존재하면 실행 명령의 종료 코드는 1입니다. 로그를 남기기 위해 첫 실패 후에도 나머지 품질 검사를 실행합니다. 실패를 숨기거나 전체 통과로 처리하지 않습니다.

## 결과 위치

- .tmp/test-results/REPORT.md: 실행 요약과 문서 ID 추적표
- cases.json / unit.xml: 개별 검사 결과와 실패 증거
- traceability.json: 문서의 139개 UT ID별 검사 연결
- coverage.xml / .tmp/coverage/index.html: Python 라인·분기 커버리지
- ruff-check.json / ruff-format.log / pyright.json: 독립 품질 게이트 결과

단일 재현 예시:

~~~powershell
.\.venv-test\Scripts\python.exe -m pytest tests/unit/workers/test_queue.py -vv
.\.venv-test\Scripts\python.exe -m pytest tests/unit --reverse-unit-order -q
~~~

반대 순서 실행은 순서 의존을 조사하는 보조 수단입니다. 2회 같은 결과가 나왔다고 향후 flaky 가능성이 없다고 단정하지 않습니다.

## 격리와 범위

각 테스트의 임시 디렉터리만 SQLite 연결을 허용합니다. 실제 data 경로는 읽기·쓰기를 차단합니다. 외부 HTTP/SMTP·모델 로드/다운로드·외부 프로세스 실행을 차단하며 TestClient는 실제 FastAPI 서버 포트를 열지 않습니다. Windows asyncio의 내부 wakeup socketpair 생성만 예외입니다. 백그라운드 요약 시작/중지는 mock입니다.

실제 Argon2 해시 및 검증은 임시 회원 데이터로 수행합니다. 시각·UUID·세션 토큰은 고정 fixture로 대체합니다. 재시도는 fake clock을 이동시켜 60초/300초를 실제로 기다리지 않습니다.

기존 tests/*.py의 순수 검사 25개를 격리 환경에서 재실행합니다. 로컬 HTTP 서버를 띄우는 기존 메서드와 tests/legacy의 JavaScript 코드는 단위 검사에 포함하지 않았으며, 별도 통합 테스트 대상입니다. 테스트 파일은 삭제하지 않았습니다.

## 문서 판정 읽는 법

- FAIL: 실행한 문서 기대값과 현재 구현이 다름. spec_gap 표시는 분류용이며 skip/xfail이 아닙니다.
- CHECKED_PARTIALLY: ID의 일부 기대결과를 검사했지만 전체 PASS라고 보장하지 않음.
- NOT_IMPLEMENTED: 예약·알림·Redis 캐시·관련 뉴스·refresh·회원탈퇴 등 해당 구현이 없음.
- DESIGN_DIFFERENCE: 설정 미리보기, 현재 카테고리, 세션 인증, RSS 기반 요약 등 문서 구조와 다름.
- NOT_COVERED: 아직 자동 검사를 작성하지 않은 범위. 구현 여부와 무관하게 미검증.

브라우저 키보드·Clipboard·CSS 크기·모바일 동작은 이 Python 커버리지에 포함되지 않습니다. 단위 테스트 완료와 브라우저 회귀 완료는 구분합니다. 원문 문서는 각 항목의 P0/P1 지정표를 제공하지 않으므로 전체 문서 완료를 임의로 판정하지 않습니다.

이메일 인증 5단계는 구현하지 않습니다. 정보 부족 상태는 정상 3줄 요약으로 바꾸지 않고 명시적인 INSUFFICIENT 처리 여부를 검증합니다.

## 백엔드 패키지 전환 이후

실제 구현은 src/backend/src/dait입니다. backend.*는 같은 모듈 객체로 연결하는 호환 경로입니다. fixture는 두 이름을 모두 인식해 기존 DB 격리를 유지합니다. 아래 과거 실행 결과는 구조 변경 전 기준이며, 이번 변경의 자동 테스트는 사용자 요청에 따라 실행하지 않았습니다.
