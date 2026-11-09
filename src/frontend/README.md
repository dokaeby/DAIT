# DAIT 프론트엔드

실제 화면은 public/의 HTML·CSS 및 HTML 내부 JavaScript로 구성한다. 별도 Node.js 빌드 설정은 없으며 백엔드가 파일을 제공한다.

| 경로 | 역할 | 상태 |
|---|---|---|
| public/index.html | 뉴스 목록·검색·필터·요약 토글 | 실행 화면 |
| public/detail.html | 뉴스 상세·원문·번역·요약 | 실행 화면 |
| public/mockup.css | 공통 테마·반응형 스타일 | 실행 스타일 |
| src/app/ | 라우팅·접근 정책 | 기존 미구현 가이드 |
| src/core/ | API 클라이언트·공개 런타임 설정 | 기존 미구현 가이드 |
| src/features/ | 인증·뉴스·설정 기능 | 기존 미구현 가이드 |

src/의 Python·TypeScript 파일은 현재 화면에서 실행되지 않는 개발 가이드다. 실제 화면은 public/에서 수정한다.

프로젝트 루트에서 실행:

    python -m uvicorn src.backend.app.api.main:app --reload

http://127.0.0.1:8000/ 에 접속한다. 화면 URL /, /detail.html 및 정적 파일 URL /mockup/*는 유지한다. API는 /v1을 사용한다. DB·Redis 접근과 뉴스 처리는 백엔드가 담당한다.

브라우저 테스트 가이드는 tests/frontend/tests/에 있다.
