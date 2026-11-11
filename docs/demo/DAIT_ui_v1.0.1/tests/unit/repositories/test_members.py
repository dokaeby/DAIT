import sqlite3
from contextlib import closing

import pytest

from backend import users


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


@pytest.mark.extension
def test_normalized_username_unique():
    users.create_user("UserA", "abcde")
    with pytest.raises(users.DuplicateUsernameError):
        users.create_user("usera", "abcde")


@pytest.mark.ut("UT-AUTH-007")
def test_invalid_credentials_same_repository_result():
    users.create_user("usr_test_a", "abcde")
    assert users.authenticate_member("usr_test_a", "wrong") is None
    assert users.authenticate_member("missing", "wrong") is None


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


@pytest.mark.extension
def test_session_expires_with_fake_clock(runtime):
    member = users.create_user("usr_test_a", "abcde")
    token = users.create_session({**member, "kind": "member"})
    runtime.clock.now += users.SESSION_MAX_AGE
    assert users.session_identity(token) is None


@pytest.mark.extension
def test_account_switch_revokes_previous_token():
    a = users.create_user("usr_test_a", "abcde")
    b = users.create_user("usr_test_b", "abcde")
    first = users.create_session({**a, "kind": "member"})
    second = users.create_session({**b, "kind": "member"}, first)
    assert users.session_identity(first) is None
    assert users.session_identity(second)["username"] == "usr_test_b"


@pytest.mark.extension
def test_interests_are_scoped_per_member():
    users.create_user("usr_test_a", "abcde")
    users.create_user("usr_test_b", "abcde")
    users.save_interests("usr_test_a", ["보안"], {})
    users.save_interests("usr_test_b", ["클라우드"], {})
    assert users.load_interests("usr_test_a", {}) == ("보안",)
    assert users.load_interests("usr_test_b", {}) == ("클라우드",)
