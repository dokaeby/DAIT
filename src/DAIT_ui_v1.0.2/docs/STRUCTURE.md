# 프로젝트 구조

- `src/dait/api/v1/`: 기존 URL을 처리하는 인증·기사·설정·관심사 라우터
- `src/dait/core/`: 경로와 모델 설정
- `src/dait/repositories/`: 회원·기사·요약 결과·작업 대기열 저장소
- `src/dait/services/`: 관심사·검색·요약 서비스
- `src/dait/pipelines/`: 수집, 모델 호출, 임베딩 및 수동 도구
- `src/frontend/`: Python 화면 렌더러와 CSS·JavaScript
- `src/backend/`: 기존 `backend.*` import를 유지하는 호환 코드
- `archive/compat_frontend_before_cleanup/`: 이전 루트 프런트엔드 보관본
- `data/`: 기존 SQLite 데이터

상세 이식 기록은 [전체 구조 이식](migration/FULL_MIGRATION.md)을 확인하세요. 호환 모듈 및 앱 import를 확인했습니다. 브라우저 회귀 테스트는 별도로 필요합니다.
