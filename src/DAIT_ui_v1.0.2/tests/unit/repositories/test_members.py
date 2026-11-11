import sqlite3
from contextlib import closing

import pytest

from backend import users


# 기능: 비밀번호 해시 저장과 검증 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-001")
def test_password_is_hashed_and_verifiable():
    member = users.create_user("usr_test_a", "private-password")
    with closing(sqlite3.connect(users.USER_DB)) as db:
        hashed = db.execute(
            "SELECT password_hash FROM users WHERE id=?", (member["id"],)
        ).fetchone()[0]
    assert hashed != "private-password"
    assert hashed.startswith("$argon2")
    assert users.password_hasher().verify("private-password", hashed)


# 기능: 정규화된 아이디의 유일성 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_normalized_username_unique():
    users.create_user("UserA", "abcde")
    with pytest.raises(users.DuplicateUsernameError):
        users.create_user("usera", "abcde")


# 기능: 잘못된 인증 정보의 동일한 저장소 결과 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-007")
def test_invalid_credentials_same_repository_result():
    users.create_user("usr_test_a", "abcde")
    assert users.authenticate_member("usr_test_a", "wrong") is None
    assert users.authenticate_member("missing", "wrong") is None


# 기능: 세션 토큰 해시와 반복 로그아웃 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-006", "UT-AUTH-010")
def test_session_hash_and_idempotent_logout():
    member = users.create_user("usr_test_a", "abcde")
    token = users.create_session({**member, "kind": "member"})
    with closing(sqlite3.connect(users.USER_DB)) as db:
        saved = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert saved == users.token_hash(token)
    assert token != saved
    assert users.session_identity(token)["username"] == "usr_test_a"
    users.revoke_session(token)
    users.revoke_session(token)
    assert users.session_identity(token) is None


# 기능: 고정 시각 변경에 따른 세션 만료 동작을 검증한다.
# 입력:
#   runtime: 격리된 DB·고정 시각·서비스 묶음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_session_expires_with_fake_clock(runtime):
    member = users.create_user("usr_test_a", "abcde")
    token = users.create_session({**member, "kind": "member"})
    runtime.clock.now += users.SESSION_MAX_AGE
    assert users.session_identity(token) is None


# 기능: 계정 전환 시 이전 토큰 폐기 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_account_switch_revokes_previous_token():
    a = users.create_user("usr_test_a", "abcde")
    b = users.create_user("usr_test_b", "abcde")
    first = users.create_session({**a, "kind": "member"})
    second = users.create_session({**b, "kind": "member"}, first)
    assert users.session_identity(first) is None
    assert users.session_identity(second)["username"] == "usr_test_b"


# 기능: 회원별 관심사 격리 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_interests_are_scoped_per_member():
    users.create_user("usr_test_a", "abcde")
    users.create_user("usr_test_b", "abcde")
    users.save_interests("usr_test_a", ["보안"], {})
    users.save_interests("usr_test_b", ["클라우드"], {})
    assert users.load_interests("usr_test_a", {}) == ("보안",)
    assert users.load_interests("usr_test_b", {}) == ("클라우드",)
