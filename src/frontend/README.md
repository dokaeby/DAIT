# Frontend 개발 목업

브라우저 앱의 라우팅, API 연결, 세션 상태, 뉴스 조회 상태, 설정 연결 책임을 모은 비실행 스캐폴드다. UI 마크업·스타일은 `docs/v1.0.0/mockup/`에서 별도로 관리하며, TypeScript 파일에는 구현 가이드만 있다.

| 경로 | 기능 ID | 책임 |
|---|---|---|
| `src/app/routes.ts` | 화면 기능 전체 | 메인·상세·설정·인증 경로와 접근 정책 |
| `src/core/api_client.ts` | 전체 | `/v1` API 통신, 오류·인증·요청 ID 처리 |
| `src/core/runtime_config.ts` | 전체 | 공개 런타임 설정 검증 |
| `src/features/auth/auth_api.ts` | FR-AUTH-01~04 | 가입·로그인·로그아웃·탈퇴 API 연결 |
| `src/features/auth/session_store.ts` | FR-AUTH-02~04 | 세션 상태와 인증 전환 |
| `src/features/news/news_api.ts` | FR-HOME-01~02, FR-SEARCH-01, FR-DETAIL-01~02 | 목록·검색·상세 API 연결 |
| `src/features/news/news_view_state.ts` | FR-HOME-02 | 로딩·빈·오류·성공 상태 모델 |
| `src/features/settings/settings_api.ts` | FR-SET-01~03 | 예약·관심·알림·정책 API 연결 |
| `tests/` | 사용자 기능 | 브라우저 수준 흐름 테스트 계획 |

FR-PIPE-01~04는 서버 전용 기능이므로 frontend에 중복 파일을 만들지 않는다.
