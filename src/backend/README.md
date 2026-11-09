# DAIT 백엔드

실행 코드는 app/에 모은다. FastAPI가 API와 정적 화면을 제공하고, 뉴스 수집·본문 추출·번역·요약·랭킹·DB·캐시를 처리한다.

| 경로 | 역할 |
|---|---|
| app/api/main.py | 앱 생성·환경설정·생명주기·화면 제공 |
| app/api/v1/news.py | 뉴스 목록·상세 API |
| app/collectors/ | RSS 수집·본문 추출 |
| app/core/ | 뉴스 분류·제목 번역 규칙 |
| app/repositories/ | DB 접근 |
| app/schemas/ | 데이터 계약 |
| app/services/ | 뉴스 조회·캐시·랭킹 |
| app/workers/ | 수집·번역·요약 파이프라인 |
| src/dait/ | 기존 기능별 개발 가이드 (미구현) |
| migrations/ | 기존 마이그레이션 가이드 |

프로젝트 루트에서 실행:

    python -m uvicorn src.backend.app.api.main:app --reload
    python -m pytest tests/backend/tests -q

화면은 src/frontend/public/, 테스트는 tests/backend/tests/에 있다. 의존성과 검사 설정은 루트에서 관리한다.
