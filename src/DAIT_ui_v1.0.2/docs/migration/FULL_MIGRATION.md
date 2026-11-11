# 전체 구조 이식

기준 프로젝트: C:/DAIT_test/DAIT_ui. 기존 API URL과 SQLite data 폴더를 유지합니다.

- 백엔드 구현: src/backend/src/dait; 기존 라우터는 api/v1, 관심사 서비스는 services에 배치했습니다. 이전 dait 모듈 경로와 backend 경로는 호환용입니다. api/v1은 소스 디렉터리 이름이며 URL에 /v1을 추가하지 않았습니다.
- 프런트엔드: src/frontend/src/frontend. Python HTML 렌더러와 CSS/JS를 옮겼습니다. 루트 frontend는 이전 경로 호환 및 원본 보존용입니다. TypeScript 전환이나 참조 프로젝트의 미구현 기능 추가는 하지 않았습니다.
- 회원·기사·요약·색인 DB는 data에 그대로 두었습니다. 일부 파이프라인 SQL 및 렌더링 코드의 세부 책임 분리는 남아 있습니다.
- 사용자 요청으로 설치, 서버, 브라우저, 기능 및 자동 테스트를 실행하지 않았습니다. 이식 후 정상 동작은 미검증입니다.
- 이메일 인증 5단계는 보류합니다.

실행 시 프로젝트 루트에서 `python -m pip install -e . --no-deps`를 다시 수행하고 `python -m uvicorn dait.main:app --host 127.0.0.1 --port 8000`으로 시작합니다.
