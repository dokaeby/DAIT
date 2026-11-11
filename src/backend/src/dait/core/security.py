"""비밀번호 해시와 토큰(JWT access, 랜덤 refresh) 도구. DB·HTTP를 모르는 순수 함수만 둔다."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel, ConfigDict, ValidationError

from dait.core.errors import InvalidTokenError

_hasher = PasswordHasher()  # argon2-cffi 기본값이 argon2id다.
# 없는 이메일로 로그인할 때도 같은 비용으로 검증하기 위한 가짜 해시
# (응답 시간으로 계정 유무를 알아내지 못하게 한다).
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-only")
_JWT_ALGORITHM = "HS256"


class AccessClaims(BaseModel):
    """access 토큰 안에 들어 있는 값."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sub: str  # 사용자 id
    jti: str  # 토큰 고유 id
    iat: int
    exp: int


def hash_password(raw: str) -> str:
    """비밀번호를 argon2id 해시로 바꾼다.

    입력: raw (사용자가 입력한 평문 비밀번호)
    출력: str (argon2id 해시 문자열, 솔트 포함)
    기능: 평문을 저장하지 않기 위해 해시만 만든다. 같은 비밀번호도 호출마다 결과가 다르다.
    """
    return _hasher.hash(raw)


def verify_password(raw: str, password_hash: str | None) -> bool:
    """평문 비밀번호가 해시와 맞는지 확인한다.

    입력: raw (입력된 평문), password_hash (저장된 해시, 사용자가 없으면 None)
    출력: bool (일치하면 True)
    기능: 사용자가 없을 때도 가짜 해시로 같은 계산을 해 시간 차이를 줄이고 항상 False를 돌려준다.
    """
    target = password_hash if password_hash is not None else _DUMMY_HASH
    try:
        matched = _hasher.verify(target, raw)
    except (VerificationError, InvalidHashError):
        return False
    return matched and password_hash is not None


def create_access_token(user_id: str, secret: str, minutes: int, now: datetime) -> str:
    """짧은 수명의 access JWT를 만든다.

    입력: user_id (사용자 id), secret (서명 키), minutes (유효 분), now (발급 기준 UTC 시각)
    출력: str (HS256으로 서명된 JWT)
    기능: sub, jti, iat, exp만 담는다. 이메일 같은 개인정보는 토큰에 넣지 않는다.
    """
    payload = {
        "sub": user_id,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> AccessClaims:
    """access JWT의 서명과 만료를 검증하고 값을 꺼낸다.

    입력: token (클라이언트가 보낸 JWT), secret (서명 키)
    출력: AccessClaims (검증된 값)
    기능: 알고리즘을 HS256으로 고정(alg=none 공격 차단)한다.
          만료·변조·필수값 누락이면 InvalidTokenError.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
        return AccessClaims.model_validate(payload)
    except (jwt.PyJWTError, ValidationError) as exc:
        raise InvalidTokenError from exc


def new_refresh_token() -> str:
    """추측할 수 없는 refresh 토큰 원문을 만든다.

    입력: 없음
    출력: str (URL에 안전한 무작위 문자열, 256비트)
    기능: secrets 모듈로 만든다. 원문은 클라이언트에게만 주고 서버에는 해시만 저장한다.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """refresh 토큰 원문의 저장용 해시를 만든다.

    입력: token (refresh 토큰 원문)
    출력: str (SHA-256 16진 문자열 64자)
    기능: 원문이 이미 256비트 난수라 느린 해시가 필요 없다. DB가 유출돼도 토큰을 되살릴 수 없다.
    """
    return hashlib.sha256(token.encode()).hexdigest()
