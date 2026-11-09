# 프로젝트 구조

- `src/backend/src/dait/api/v1/`: 기존 URL을 처리하는 인증·기사·설정·관심사 라우터
- `src/backend/src/dait/core/`: 경로와 모델 설정
- `src/backend/src/dait/repositories/`: 회원·기사·요약 결과·작업 대기열 저장소
- `src/backend/src/dait/services/`: 관심사·검색·요약 서비스
- `src/backend/src/dait/pipelines/`: 수집, 모델 호출, 임베딩 및 수동 도구
- `src/frontend/src/frontend/`: Python 화면 렌더러와 CSS·JavaScript
- `backend/`, 루트 `frontend/` 및 `dait`의 기존 라우터 모듈: 이전 경로 호환 또는 보존용
- `data/`: 기존 SQLite 데이터

상세 이식 기록은 [전체 구조 이식](migration/FULL_MIGRATION.md)을 확인하세요. 기능 실행은 아직 검증되지 않았습니다.
