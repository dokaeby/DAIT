# 구조 전환 2단계: 백엔드 패키지·설정·저장소 이동

기준일: 2026-11-09 / Asia/Seoul. 사용자가 1단계 기존 기능 정상 작동을 확인했습니다. 이번 2단계는 사용자 테스트 대기입니다.

## 적용 범위

작업 기준은 C:/DAIT_test/DAIT_ui입니다. 이 프로젝트 안에 src/backend/src/dait 패키지를 만들었습니다. C:/DAIT/src의 참조용 스캐폴드는 변경하지 않았습니다.

- dait/core/config.py: 기존 DB 경로·모델명·화면 경로. 기본 루트는 DAIT_ui이며 data 폴더는 이동하지 않습니다.
- dait/repositories/user_repository.py: 기존 회원·세션·관심사 저장. 기존 함수와 트랜잭션·해시·세션 규칙을 보존합니다.
- news_repository.py: 목록·맞춤 목록·상세·카테고리·원문 URL·국내 저장 요약 조회.
- result_repository.py: 국내/해외 요약 테이블 정의 및 자동 작업자의 결과 저장, 해외 결과 조회.
- job_repository.py: 대기열 생성·등록·claim·상태·재시도 기록·복구·수동 재요청 SQL.
- dait/services, dait/pipelines: 기존 동작을 새 패키지 import로 연결.

아직 라우터/서비스를 api/v1로 나누거나 API 응답 계약을 바꾸지 않았습니다. 프런트엔드와 기존 URL 19개도 그대로입니다. 기존 단독 HTTP Handler와 CLI 내부의 일부 DB 처리, 회원 모듈에 남은 인증 정책은 후속 책임 분리 때 다룹니다. Redis·PostgreSQL·새 인증·외부 AI API를 도입하지 않았습니다.

## 실행 준비 (한 번)

기존 서버가 꺼진 상태로 DAIT_ui 루트에서 실행합니다.

~~~powershell
cd C:\DAIT_test\DAIT_ui
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m uvicorn dait.main:app --host 127.0.0.1 --port 8000
~~~

기존 서비스 의존성은 유지합니다. editable 설치는 소스를 복사하지 않고 개발 패키지로 등록합니다. --no-deps는 이미 설치한 서비스 의존성을 다시 설치하지 않기 위한 옵션이며, 빌드용 setuptools 준비가 필요할 수 있습니다. 모델 다운로드·기사 수집·서버 실행은 제가 수행하지 않았습니다.

기존 backend.main:app과 python -m backend.pipelines.collect_news 명령도 호환 연결을 통해 동작하도록 작성했습니다. 새로 수정할 실제 소스는 dait에 두고 backend의 호환 파일에 기능을 추가하지 않습니다. 예전 import와 새 import는 같은 모듈 객체를 가리키므로 테스트의 monkeypatch와 세션·검색·작업 상태가 이중 생성되지 않도록 설계했습니다. 실제 import 동작 확인은 사용자 테스트 항목입니다.

수집 권장 명령:

~~~powershell
.\.venv\Scripts\python.exe -m dait.pipelines.collect_news
~~~

## 사용자 확인 순서

1. 설치와 서버 시작에서 ImportError가 없는지 확인하고 Ctrl+F5로 갱신합니다.
2. 기존 회원으로 로그인하고 관심사·맞춤 목록·계정 전환·동일 계정 재로그인·로그아웃을 확인합니다.
3. 통합 검색에서 기존 유사도·순위·필터를 확인합니다.
4. 메인·팝업의 기존 요약과 원문 링크를 확인합니다.
5. 필요한 경우 새 명령으로 수집하여 자동 요약·대기 상태·팝업 갱신을 확인합니다. 새 기사가 없으면 관련 항목은 미실행으로 남깁니다.
6. 서버를 재시작하고 회원·관심사·저장 요약이 유지되는지 확인합니다.
7. 기존 명령 호환이 필요한 경우 서버를 종료한 뒤 backend.main:app으로도 시작해 같은 data를 읽는지 확인합니다. 두 서버를 동시에 실행하지 않습니다.

검사 기준은 BASELINE.md의 B01~B14를 계속 사용합니다. 아직 실행하지 않은 항목을 성공으로 기록하지 않습니다.

## 확인한 것과 확인하지 않은 것

- Python AST 문법·로컬 import 대상·패키지 메타데이터·기본 경로를 정적으로 확인했습니다.
- 원본 SQL 문자열 리터럴 82개의 내용과 개수가 이동 후에도 동일함을 대조했습니다. 이는 DB 쿼리 실행이나 동작 테스트를 대신하지 않습니다.
- 서버·브라우저·모델·자동 테스트·editable 설치를 실행하지 않았습니다.
- 기존 106통과/12실패는 이동 전 자동 테스트 결과이며 이동 후 결과로 취급하지 않습니다.

테스트 fixture는 backend.*와 dait.* 모두를 인식하도록 수정했고 pytest 소스 경로·커버리지·Pyright 대상도 새 구조에 맞췄습니다. 자동 검사를 나중에 실행할 때는 테스트 가상환경에도 pip install -e . --no-deps를 한 번 수행합니다.

원본 소스는 archive에 별도 보관합니다. data DB는 이번 반영 작업에서 읽기 해시 대조 외에 열거나 수정하지 않습니다. 반영 전후 6개 DB 해시는 로컬 .tmp/migration-step2에 기록합니다. 사용자 테스트 실행 이후에는 데이터가 정상적으로 달라질 수 있습니다.

사용자 테스트 확인 후에만 다음 서비스·라우터 분리 단계로 넘어갑니다. 이메일 인증 5단계 보류 조건도 그대로입니다.
