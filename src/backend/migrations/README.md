# 마이그레이션 목업

담당 기능은 DAIT 전체 영속 데이터의 Alembic 변경 이력 관리다.

구현 시에는 모델 변경 승인 후 revision을 생성하고, PostgreSQL과 SQLite 양쪽에서 upgrade/downgrade를 검증한다. 사용자·세션·설정의 소유권/RLS, canonical URL과 dedupe key의 unique 제약, 감사·작업 이력 보존을 포함한다. 실제 migration 파일과 SQL은 아직 만들지 않았다.
