# Backend 개발 목업

FastAPI, 서비스, 저장소, worker, collector, migration 책임을 모은 비실행 스캐폴드다. Python 파일에는 구현 가이드만 있으며 실제 함수·클래스·API 동작은 없다.

| 경로 | 책임 |
|---|---|
| `src/dait/api/v1/` | HTTP 요청·응답 경계와 인증 의존성 |
| `src/dait/services/` | 16개 기능별 유스케이스와 트랜잭션 조정 |
| `src/dait/repositories/` | PostgreSQL/SQLite와 Redis 접근 |
| `src/dait/schemas/` | Pydantic v2 경계 모델 |
| `src/dait/core/` | 설정, 보안, 로깅, 오류 정책 |
| `src/dait/workers/` | 수집·AI 처리·알림·예약 비동기 실행 |
| `src/dait/collectors/` | 승인 뉴스 소스 어댑터 |
| `tests/` | 단위·통합 테스트 계획 |
| `migrations/` | Alembic 변경 계획 |
| `config/` | 비밀값 없는 환경변수 명세 |
