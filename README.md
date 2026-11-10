# DAIT

AI 뉴스 수집·번역·요약 큐레이션 서비스.

- **백엔드**: src/backend/app/ — FastAPI, 수집·번역·요약·랭킹, DB·캐시.
- **프론트엔드**: src/frontend/public/ — HTML·CSS·JavaScript 뉴스 화면.
- **테스트**: tests/backend/tests/, tests/frontend/tests/.

자세한 폴더 역할과 기존 개발 가이드 구분은 [소스 구조](src/README.md)를 참고한다.

프로젝트 루트에서 의존성을 설치한 Python 환경으로 실행한다.

    python -m uvicorn src.backend.app.api.main:app --reload

접속 주소: http://127.0.0.1:8000/
