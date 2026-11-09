# DAIT 소스 구조

실행 코드는 백엔드와 프론트엔드로 나누고, 기존 설계 가이드는 보존한다.

| 경로 | 역할 | 상태 |
|---|---|---|
| backend/app/api/ | FastAPI 진입점·뉴스 목록/상세 API | 실행 코드 |
| backend/app/collectors/ | RSS 수집·기사 본문 추출 | 실행 코드 |
| backend/app/core/ | 뉴스 분류·제목 번역 규칙 | 실행 코드 |
| backend/app/repositories/ | SQLAlchemy 비동기 DB 접근 | 실행 코드 |
| backend/app/schemas/ | Pydantic 데이터 모델 | 실행 코드 |
| backend/app/services/ | 뉴스 조회·캐시·랭킹 | 실행 코드 |
| backend/app/workers/ | 수집·번역·요약 처리 | 실행 코드 |
| frontend/public/index.html | 뉴스 목록·검색·필터·요약 토글 | 실행 화면 |
| frontend/public/detail.html | 뉴스 상세·원문·번역·요약 | 실행 화면 |
| frontend/public/mockup.css | 공통 테마·반응형 스타일 | 실행 스타일 |
| backend/src/dait/ | 기존 기능별 개발 가이드 | 미구현 가이드 |
| backend/migrations/ | 마이그레이션 가이드 | 미구현 가이드 |
| frontend/src/ | Python·TypeScript 라우팅·API·기능별 개발 가이드 | 미구현 가이드 |

## 실행과 테스트

프로젝트 루트에서 의존성을 설치한 Python 환경으로 실행한다.

    python -m uvicorn src.backend.app.api.main:app --reload
    python -m pytest tests/backend/tests -q

백엔드는 /, /detail.html, /mockup/* 에서 frontend/public 파일을 제공한다. 기존 API 주소 /v1/news 등은 유지한다. 프론트엔드는 별도 빌드 과정이 없다.

- tests/backend/tests/: 백엔드 테스트 및 미구현 기능 테스트 가이드.
- tests/frontend/tests/: 브라우저 흐름 테스트 가이드.
- 루트 pyproject.toml, requirements.txt, uv.lock: 공통 Python 의존성·검사 설정.
- 루트 Procfile: 배포 실행 명령.
- docs/의 목업·데모: 설계·참고 자료. 실제 화면 수정은 frontend/public/에서 진행한다.

기존 backend/src/dait/와 frontend/src/ 파일은 실제 구현이 아닌 개발 가이드다.
