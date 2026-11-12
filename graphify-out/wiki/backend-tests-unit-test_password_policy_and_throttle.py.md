# backend/tests/unit/test_password_policy_and_throttle.py

> 25 nodes

## Key Concepts

- **backend/tests/unit/test_password_policy_and_throttle.py** (24 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_common_passwords_are_weak()** (3 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_default_thresholds_are_account_5_and_ip_20()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_lock_doubles_and_is_capped_at_15_minutes()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_locked_at_threshold_for_60_seconds()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_old_failures_are_forgotten()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_password_containing_email_local_part_is_weak()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_short_local_part_is_not_compared()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_strong_password_is_allowed()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_clear_resets_failures()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_keys_are_independent()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_not_locked_before_threshold()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **parametrize** (1 connections)
- **비밀번호 정책(흔한 값, 이메일 포함)과 로그인 잠금 테스트.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **흔한 비밀번호는 대소문자와 관계없이 막는다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **이메일 앞부분을 포함한 비밀번호는 막는다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **앞부분이 3자 미만이면 우연히 겹치기 쉬워 비교하지 않는다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **흔하지 않고 이메일과 무관한 비밀번호는 통과한다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **기준 횟수에 닿으면 60초 잠기고 그 뒤에 풀린다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **실패가 늘수록 잠금이 두 배로 길어지고 15분을 넘지 않는다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **마지막 실패가 15분보다 오래됐으면 횟수를 새로 센다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **기본 잠금은 계정 5회, IP 20회부터다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **ambiguous_python_import_050a5f9e2ed0** (1 connections)
- **ambiguous_python_import_0e1370f716db** (1 connections)
- **ambiguous_python_import_2157d32c7b10** (1 connections)

## Relationships

- [RedisThrottle](RedisThrottle.md) (6 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [_FakeRedis](_FakeRedis.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_password_policy_and_throttle.py`

## Audit Trail

- EXTRACTED: 33 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*