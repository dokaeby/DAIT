# DAIT 전체 프로젝트 개발 목업

이 디렉터리는 DAIT v1.0.0 상세기획서와 상세기능설계서를 실제 개발 구조로 옮긴 **비실행 스캐폴드**다. `backend/`와 `frontend/`를 분리했으며 모든 코드 파일에는 구현 가이드만 있다. 함수, 클래스, API 동작, DB 처리, 화면 렌더링 같은 실제 기능은 없다.

## 구조

| 경로 | 기능 ID | 개발 시 역할 |
|---|---|---|
| `backend/src/dait/api/v1/` | 전체 | FastAPI 라우트, 요청·응답 경계, 인증 의존성 |
| `backend/src/dait/services/` | FR 16종 | 기능별 유스케이스와 트랜잭션 조정 |
| `backend/src/dait/repositories/` | 전체 | PostgreSQL/SQLite 및 Redis 접근 |
| `backend/src/dait/schemas/` | 전체 | Pydantic v2 입력·출력·외부 데이터 모델 |
| `backend/src/dait/core/` | 전체 | 설정, 보안, 로깅, 오류 정책 |
| `backend/src/dait/workers/` | FR-PIPE-01~04, FR-SET-01~03 | 비동기 작업, 예약, 알림 실행 |
| `backend/src/dait/collectors/` | FR-PIPE-01 | 승인된 뉴스 소스 어댑터 |
| `backend/tests/` | 전체 | backend 단위·통합 검증 계획 |
| `backend/migrations/` | 전체 | Alembic 변경 계획 |
| `backend/config/.env.example` | 전체 | 비밀값 없는 환경변수 명세 |
| `frontend/src/app/` | 사용자 화면 기능 | 라우팅과 접근 정책 |
| `frontend/src/core/` | 전체 | API client와 공개 런타임 설정 |
| `frontend/src/features/auth/` | FR-AUTH-01~04 | 인증 API와 세션 상태 |
| `frontend/src/features/news/` | FR-HOME, FR-SEARCH, FR-DETAIL | 뉴스 API와 조회 상태 |
| `frontend/src/features/settings/` | FR-SET-01~03 | 설정 API 연결 |
| `frontend/tests/` | 사용자 화면 기능 | 브라우저 흐름 검증 계획 |

## Backend 기능별 서비스 파일

| 파일 | 기능 ID | 담당 기능 |
|---|---|---|
| `signup_service.py` | FR-AUTH-01 | 이메일 회원가입 |
| `social_auth_service.py` | FR-AUTH-02 | 소셜 회원가입·로그인 |
| `session_service.py` | FR-AUTH-03 | 로그인·로그아웃 |
| `account_deletion_service.py` | FR-AUTH-04 | 회원탈퇴 |
| `news_feed_service.py` | FR-HOME-01 | 랭킹 카드 |
| `news_search_service.py` | FR-SEARCH-01 | 뉴스 검색·초기화 |
| `feed_state_service.py` | FR-HOME-02 | 로딩·빈·오류 상태 계약 |
| `news_detail_service.py` | FR-DETAIL-01 | 뉴스 상세 콘텐츠 |
| `source_action_service.py` | FR-DETAIL-02 | 원문 열기·링크 복사 데이터 |
| `schedule_service.py` | FR-SET-01 | 예약 |
| `preference_service.py` | FR-SET-02 | 검색·관심 설정 |
| `notification_policy_service.py` | FR-SET-03 | 노출·알림·정책 |
| `collection_service.py` | FR-PIPE-01 | 뉴스 수집 |
| `translation_summary_service.py` | FR-PIPE-02 | 번역·3줄 요약 |
| `ranking_relation_service.py` | FR-PIPE-03 | 랭킹·관련 뉴스 |
| `cache_retry_service.py` | FR-PIPE-04 | 캐시·재처리 |

## 개발 원칙

- API, 외부 소스, LLM, DB, Redis 경계는 `extra="forbid"`인 Pydantic 모델로 검증한다.
- 라우터는 서비스를 호출하고, 서비스는 저장소 인터페이스를 통해 데이터에 접근한다.
- 사용자 소유 데이터는 인증 주체와 소유권을 함께 확인해 IDOR를 차단한다.
- 외부 URL은 허용 목록과 SSRF 방어를 적용하고, 비밀값·개인정보·토큰을 로그에 남기지 않는다.
- DB의 검증 완료 데이터를 원본으로 사용하며 Redis는 TTL 캐시·큐·속도 제한·락에만 사용한다.
- frontend는 backend의 `/v1` 계약만 사용하며 파이프라인·DB·Redis에 직접 접근하지 않는다.
- 화면 마크업과 스타일은 별도 `docs/v1.0.0/mockup/`에서 관리한다.
