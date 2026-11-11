"""테스트 공용 도구: 타입 고정된 HTTP 클라이언트와 Alembic 설정."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import httpx2
import jwt
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[3] / "src" / "backend"


def forge_token(payload: Mapping[str, object], key: str, algorithm: str) -> str:
    """검증 우회 시도용 토큰을 원하는 알고리즘으로 만든다.

    입력: payload (토큰에 넣을 값), key (서명 키), algorithm (예: HS256, none)
    출력: str (JWT 문자열)
    기능: 보안 테스트가 변조·alg=none 토큰을 만들 때만 쓴다.
    """
    return jwt.encode(dict(payload), key, algorithm=algorithm)


def read_claim_names(token: str, key: str) -> set[str]:
    """토큰에 들어 있는 값의 이름 목록을 돌려준다.

    입력: token (HS256 JWT), key (서명 키)
    출력: set[str] (payload의 키 이름)
    기능: 토큰에 불필요한 개인정보가 없는지 확인할 때 쓴다.
    """
    return set(jwt.decode(token, key, algorithms=["HS256"]))


class HttpClient(Protocol):
    """TestClient 중 테스트에서 쓰는 부분만 타입으로 고정한다.

    starlette TestClient는 httpx 내부 타입을 참조해 pyright strict에서 Unknown이 되므로,
    경계에서 이 Protocol로 받아 타입 오류를 설정 완화 없이 막는다.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        content: bytes | None = None,
        json: Mapping[str, object] | None = None,
    ) -> httpx2.Response: ...


def as_client(app: FastAPI) -> HttpClient:
    """앱을 감싼 테스트 클라이언트를 HttpClient 타입으로 돌려준다(서버 오류도 응답으로 받는다)."""
    return TestClient(app, raise_server_exceptions=False)


def alembic_config(database_url: str) -> Config:
    """프로젝트 Alembic 설정에 테스트용 DB 주소를 끼워 돌려준다.

    입력: database_url (sqlite:///경로 형식)
    출력: Config (command.upgrade/downgrade에 넘길 설정)
    기능: 현재 폴더와 상관없이 프로젝트 루트의 alembic.ini와 migrations를 쓴다.
    """
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
