# DAIT 백엔드 개발 패키지

실제 구현은 src/dait이며 개발 등록은 전체 프로젝트 루트의 pyproject.toml을 사용합니다.

- 설정: src/dait/core/config.py
- 저장소: src/dait/repositories/
- 현재 서비스·파이프라인: src/dait/services, pipelines
- 현재 라우터: src/dait/auth.py, interests.py, settings.py, compatibility.py

진입점은 dait.main:app입니다. 경로 전환 안내는 프로젝트 루트 docs/migration/STEP2.md를 참고하세요. API v1·스키마 세분화는 다음 단계이며 이번에는 기존 URL을 보존합니다.
