# DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py

> 17 nodes

## Key Concepts

- **DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py** (18 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **Digest** (11 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/schemas.py`
- **_connect()** (10 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **DigestItem** (6 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/schemas.py`
- **add_digest()** (4 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **list_digests()** (4 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **load_settings()** (4 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **_ensure_tables()** (3 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **save_settings()** (3 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **scheduled_owners()** (3 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **mark_seen()** (2 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **unseen_count()** (2 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **Connection** (2 connections)
- **설정·예약 소식함 저장소. 회원 DB(users.db)에 별도 테이블로 둡니다. 소유자는 username_key로 구분합니다. DB 회원과…** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **(설정, 저장 시각, 마지막 예약 실행 시각). 저장한 적 없으면 None.** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **소식을 저장합니다. 예약 실행이면 같은 예약 시각으로 두 번 저장되지 않게 막고 False를 돌려줍니다.** (1 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- **ambiguous_python_import_acc6b54ef132** (1 connections)

## Relationships

- [DAIT_ui_v1.0.1/src/backend/src/dait/services/settings_service.py](DAIT_ui_v1.0.1-src-backend-src-dait-services-settings_service.py.md) (5 shared connections)
- [typing](typing.md) (5 shared connections)
- [test_settings.py](test_settings.py.md) (5 shared connections)
- [DAIT_ui_v1.0.1/src/backend/src/dait/api/v1/settings_routes.py](DAIT_ui_v1.0.1-src-backend-src-dait-api-v1-settings_routes.py.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py`
- `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/schemas.py`

## Audit Trail

- EXTRACTED: 41 (85%)
- INFERRED: 7 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*