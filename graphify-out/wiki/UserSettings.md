# UserSettings

> God node · 37 connections · `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/schemas.py`

**Community:** [test_settings.py](test_settings.py.md)

## Connections by Relation

### calls
- settings_state() `EXTRACTED`
- load_settings() `EXTRACTED`

### contains
- dait/schemas.py `EXTRACTED`

### imports
- [DAIT_ui_v1.0.1/src/backend/src/dait/services/settings_service.py](DAIT_ui_v1.0.1-src-backend-src-dait-services-settings_service.py.md) `EXTRACTED`
- [DAIT_ui_v1.0.1/src/backend/src/dait/api/v1/settings_routes.py](DAIT_ui_v1.0.1-src-backend-src-dait-api-v1-settings_routes.py.md) `EXTRACTED`
- [DAIT_ui_v1.0.1/src/backend/src/dait/repositories/settings_repository.py](DAIT_ui_v1.0.1-src-backend-src-dait-repositories-settings_repository.py.md) `EXTRACTED`

### inherits
- BaseModel `EXTRACTED`

### method
- .clean_keywords() `EXTRACTED`
- .unique_categories() `EXTRACTED`

### rationale_for
- 설정 화면 전체 저장 단위. 화면과 API가 같은 모델을 씁니다. `EXTRACTED`

### references
- 파일과 계층 `INFERRED`

### uses
- create_digest() `INFERRED`
- pick_digest_items() `INFERRED`
- put_settings() `INFERRED`
- due_at() `INFERRED`
- save_settings() `INFERRED`
- is_due() `INFERRED`
- next_run() `INFERRED`
- load_settings() `INFERRED`
- order_categories() `INFERRED`
- test_settings_are_saved_and_restored() `INFERRED`
- scheduled_owners() `INFERRED`
- save_settings() `INFERRED`
- test_digest_picks_new_matching_articles_with_reasons() `INFERRED`
- test_multiple_times_fire_latest_passed_slot_and_next_run() `INFERRED`
- test_next_run_skips_to_next_selected_day() `INFERRED`
- test_schedule_is_due_once_after_its_time() `INFERRED`
- test_schedule_needs_a_source_and_known_fields() `INFERRED`
- test_schedule_not_due_on_other_day_before_time_disabled_or_saved_later() `INFERRED`
- test_scheduler_creates_one_digest_per_slot() `INFERRED`
- test_settings_api_requires_login() `INFERRED`
- *…and 6 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*