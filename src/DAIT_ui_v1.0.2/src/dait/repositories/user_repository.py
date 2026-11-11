"""회원 저장소. 기사 DB와 분리해 회원가입 데이터만 저장합니다."""
import sqlite3
import hashlib
import secrets
import time
import unicodedata
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from pwdlib import PasswordHash

from dait.core.config import USER_DB
SESSION_MAX_AGE = 24 * 60 * 60


class DuplicateUsernameError(ValueError):
    pass


class DuplicateNicknameError(ValueError):
    pass


# 기능: 사용자 이름을 유니코드 정규화하고 공백·대소문자 차이를 제거한다.
# 입력:
#   username (str): 사용자 아이디.
# 출력: 계정 비교용 문자열.
def username_key(username: str) -> str:
    return unicodedata.normalize("NFKC", username).strip().casefold()


# 기능: 권장 비밀번호 해시 도구를 만들고 캐시한다.
# 입력: 없음.
# 출력: PasswordHash 인스턴스.
@lru_cache(maxsize=1)
def password_hasher() -> PasswordHash:
    return PasswordHash.recommended()


# 기능: 회원·세션·관심사 테이블과 필요한 컬럼을 준비한다.
# 입력: 없음.
# 출력: None. 회원 DB 스키마를 생성·갱신한다.
def initialize_auth_db() -> None:
    USER_DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            username_key TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
        if "nickname" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN nickname TEXT")
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            test_username TEXT,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            CHECK ((user_id IS NOT NULL AND test_username IS NULL)
                   OR (user_id IS NULL AND test_username IS NOT NULL))
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
        db.execute("""CREATE TABLE IF NOT EXISTS interest_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            test_username TEXT UNIQUE,
            updated_at TEXT NOT NULL,
            CHECK ((user_id IS NOT NULL AND test_username IS NULL)
                   OR (user_id IS NULL AND test_username IS NOT NULL))
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS interest_categories (
            profile_id INTEGER NOT NULL REFERENCES interest_profiles(id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            PRIMARY KEY (profile_id,category)
        )""")
        db.commit()


# 기능: 중복 아이디·닉네임을 검사하고 비밀번호 해시와 회원을 저장한다.
# 입력:
#   username (str): 사용자 아이디.
#   password (str): 검증 또는 해시할 비밀번호.
#   nickname (str | None): 화면에 표시할 닉네임.
# 출력: id, username, created_at 사전. 중복 시 전용 예외.
def create_user(username: str, password: str, nickname: str | None = None) -> dict:
    key = username_key(username)
    initialize_auth_db()
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        if db.execute("SELECT 1 FROM users WHERE username_key=?", (key,)).fetchone():
            raise DuplicateUsernameError("이미 사용 중인 아이디입니다.")

    # 느린 해시 계산 중에는 DB 쓰기 트랜잭션을 유지하지 않습니다.
    hashed = password_hasher().hash(password)
    created_at = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            if nickname and any(username_key(row[0]) == username_key(nickname) for row in db.execute("SELECT nickname FROM users WHERE nickname IS NOT NULL")):
                raise DuplicateNicknameError("이미 사용 중인 닉네임입니다.")
            cursor = db.execute("INSERT INTO users (username,username_key,password_hash,created_at,nickname) VALUES (?,?,?,?,?)",
                                (username, key, hashed, created_at, nickname))
            db.commit()
        except sqlite3.IntegrityError as exc:
            db.rollback()
            # 동시 가입 요청도 UNIQUE 제약으로 중복 저장을 막습니다.
            if exc.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                raise DuplicateUsernameError("이미 사용 중인 아이디입니다.") from exc
            raise
        return {"id": cursor.lastrowid, "username": username, "created_at": created_at}


# 기능: 사용자에게 저장된 표시 닉네임을 조회한다.
# 입력:
#   username (str | None): 사용자 아이디.
# 출력: 닉네임 문자열 또는 None.
def display_nickname(username: str | None) -> str | None:
    if not username:
        return None
    with closing(sqlite3.connect(USER_DB.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        row = db.execute("SELECT nickname FROM users WHERE username_key=?", (username_key(username),)).fetchone()
    return (row[0] if row and row[0] else None)


# 기능: 중복 여부를 검사하고 회원 닉네임을 변경한다.
# 입력:
#   username (str): 사용자 아이디.
#   nickname (str): 화면에 표시할 닉네임.
# 출력: 회원이 있으면 True, 없으면 False. 중복 시 전용 예외.
def update_nickname(username: str, nickname: str) -> bool:
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id FROM users WHERE username_key=?", (username_key(username),)).fetchone()
        if row is None:
            return False
        if nickname and any(username_key(other[0]) == username_key(nickname) for other in db.execute("SELECT nickname FROM users WHERE id != ? AND nickname IS NOT NULL", (row[0],))):
            raise DuplicateNicknameError("이미 사용 중인 닉네임입니다.")
        db.execute("UPDATE users SET nickname=? WHERE id=?", (nickname or None, row[0]))
        db.commit()
        return True


# 기능: 없는 계정도 비밀번호 검증을 수행하도록 대체 해시를 캐시한다.
# 입력: 없음.
# 출력: 대체 비밀번호 해시 문자열.
@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return password_hasher().hash("not-a-real-member-password")


# 기능: 아이디와 비밀번호 해시를 확인해 회원을 인증한다.
# 입력:
#   username (str): 사용자 아이디.
#   password (str): 검증 또는 해시할 비밀번호.
# 출력: 회원 식별 사전 또는 인증 실패 시 None.
def authenticate_member(username: str, password: str) -> dict | None:
    with closing(sqlite3.connect(USER_DB.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT id,username,password_hash FROM users WHERE username_key=?", (username_key(username),)).fetchone()
    saved_hash = row["password_hash"] if row else dummy_password_hash()
    valid = password_hasher().verify(password, saved_hash)
    if not row or not valid:
        return None
    return {"id": row["id"], "username": row["username"], "kind": "member"}


# 기능: 세션 토큰을 SHA-256으로 해시한다.
# 입력:
#   token (str): 세션 토큰.
# 출력: 16진수 해시 문자열.
def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# 기능: 새 세션을 저장하고 이전 세션과 만료된 세션을 폐기한다.
# 입력:
#   identity (dict): 사용자 ID·이름·계정 종류를 담은 사전.
#   previous_token (str | None): 폐기할 이전 세션 토큰(없으면 None).
# 출력: 새 세션의 원본 토큰 문자열.
def create_session(identity: dict, previous_token: str | None = None) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    member_id = identity["id"] if identity["kind"] == "member" else None
    test_username = identity["username"] if identity["kind"] == "test" else None
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            db.execute("INSERT INTO sessions (token_hash,user_id,test_username,created_at,expires_at) VALUES (?,?,?,?,?)",
                       (token_hash(token), member_id, test_username, now, now + SESSION_MAX_AGE))
            if previous_token:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(previous_token),))
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
    return token


# 기능: 토큰 형식과 만료 시각을 검사해 세션 사용자를 찾는다.
# 입력:
#   token (str | None): 세션 토큰.
# 출력: 사용자 식별 사전 또는 None.
def session_identity(token: str | None) -> dict | None:
    if not token or len(token) != 43:
        return None
    with closing(sqlite3.connect(USER_DB.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("""SELECT u.id,u.username,s.test_username FROM sessions s
            LEFT JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>?""", (token_hash(token), int(time.time()))).fetchone()
    if not row:
        return None
    if row["test_username"] is not None:
        return {"id": None, "username": row["test_username"], "kind": "test"}
    if row["id"] is not None:
        return {"id": row["id"], "username": row["username"], "kind": "member"}
    return None


# 기능: 해당 토큰의 세션을 삭제한다.
# 입력:
#   token (str | None): 세션 토큰.
# 출력: None. 유효하지 않은 토큰은 무시한다.
def revoke_session(token: str | None) -> None:
    if not token or len(token) != 43:
        return
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        with db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))


# 기능: 관심사 소유자를 실제 회원 또는 테스트 계정으로 구분한다.
# 입력:
#   db: 열린 SQLite 연결.
#   username (str): 사용자 아이디.
#   test_defaults (dict): 테스트 계정별 기본 관심사 사전.
# 출력: (회원 ID 또는 None, 테스트 계정명 또는 None) 튜플.
def _preference_owner(db, username: str, test_defaults: dict) -> tuple[int | None, str | None]:
    tests = {username_key(name): name for name in test_defaults}
    test_name = tests.get(username_key(username))
    if test_name:
        return None, test_name
    row = db.execute("SELECT id FROM users WHERE username_key=?", (username_key(username),)).fetchone()
    if row is None:
        raise ValueError("회원 정보를 찾을 수 없습니다. 다시 로그인해주세요.")
    return row[0], None


# 기능: 소유자의 관심사 프로필을 조회한다.
# 입력:
#   db: 열린 SQLite 연결.
#   member_id: 실제 회원 ID 또는 None.
#   test_name: 테스트 계정 이름 또는 None.
# 출력: 프로필 ID를 담은 행 또는 None.
def _preference_profile(db, member_id, test_name):
    if member_id is not None:
        return db.execute("SELECT id FROM interest_profiles WHERE user_id=?", (member_id,)).fetchone()
    return db.execute("SELECT id FROM interest_profiles WHERE test_username=?", (test_name,)).fetchone()


# 기능: 저장된 관심사나 테스트 계정의 기본 관심사를 읽는다.
# 입력:
#   username (str): 사용자 아이디.
#   test_defaults (dict): 테스트 계정별 기본 관심사 사전.
# 출력: 선택 순서대로 정렬한 카테고리 튜플.
def load_interests(username: str, test_defaults: dict) -> tuple[str, ...]:
    with closing(sqlite3.connect(USER_DB.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        member_id, test_name = _preference_owner(db, username, test_defaults)
        profile = _preference_profile(db, member_id, test_name)
        if profile is None:
            return tuple(test_defaults.get(test_name, ()))
        return tuple(row[0] for row in db.execute("SELECT category FROM interest_categories WHERE profile_id=? ORDER BY sort_order,category", (profile[0],)))


# 기능: 프로필 또는 기본 관심사로 초기 설정 완료 여부를 판단한다.
# 입력:
#   username (str): 사용자 아이디.
#   test_defaults (dict): 테스트 계정별 기본 관심사 사전.
# 출력: 설정 완료 여부(bool).
def interest_onboarding_complete(username: str, test_defaults: dict) -> bool:
    with closing(sqlite3.connect(USER_DB.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        member_id, test_name = _preference_owner(db, username, test_defaults)
        # 저장한 프로필(빈 목록 포함)은 저장 또는 '다음에 하기' 완료를 의미합니다.
        return _preference_profile(db, member_id, test_name) is not None or bool(test_defaults.get(test_name, ()))


# 기능: 기존 관심사를 유지하며 초기 설정 건너뛰기를 저장한다.
# 입력:
#   username (str): 사용자 아이디.
#   test_defaults (dict): 테스트 계정별 기본 관심사 사전.
# 출력: None. 필요한 경우 빈 프로필 또는 기본 관심사를 저장한다.
def skip_interest_onboarding(username: str, test_defaults: dict) -> None:
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            db.execute("BEGIN IMMEDIATE")
            member_id, test_name = _preference_owner(db, username, test_defaults)
            if _preference_profile(db, member_id, test_name) is None:
                cursor = db.execute("INSERT INTO interest_profiles (user_id,test_username,updated_at) VALUES (?,?,?)",
                                    (member_id, test_name, datetime.now(timezone.utc).isoformat()))
                if test_name:
                    db.executemany("INSERT INTO interest_categories (profile_id,category,sort_order) VALUES (?,?,?)",
                                   [(cursor.lastrowid, category, index) for index, category in enumerate(test_defaults.get(test_name, ()))])
            # 이미 저장한 카테고리가 있다면 그대로 보존합니다.


# 기능: 중복 카테고리를 제거하고 관심사를 선택 순서대로 교체한다.
# 입력:
#   username (str): 사용자 아이디.
#   categories (list[str]): 카테고리 목록.
#   test_defaults (dict): 테스트 계정별 기본 관심사 사전.
# 출력: 저장한 카테고리 튜플. 빈 선택이면 ValueError.
def save_interests(username: str, categories: list[str], test_defaults: dict) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(categories))
    if not selected:
        raise ValueError("관심 카테고리를 한 개 이상 선택해주세요.")
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            db.execute("BEGIN IMMEDIATE")
            member_id, test_name = _preference_owner(db, username, test_defaults)
            profile = _preference_profile(db, member_id, test_name)
            now = datetime.now(timezone.utc).isoformat()
            if profile is None:
                cursor = db.execute("INSERT INTO interest_profiles (user_id,test_username,updated_at) VALUES (?,?,?)", (member_id, test_name, now))
                profile_id = cursor.lastrowid
            else:
                profile_id = profile[0]
                db.execute("UPDATE interest_profiles SET updated_at=? WHERE id=?", (now, profile_id))
            db.execute("DELETE FROM interest_categories WHERE profile_id=?", (profile_id,))
            db.executemany("INSERT INTO interest_categories (profile_id,category,sort_order) VALUES (?,?,?)",
                           [(profile_id, category, index) for index, category in enumerate(selected)])
    return selected
