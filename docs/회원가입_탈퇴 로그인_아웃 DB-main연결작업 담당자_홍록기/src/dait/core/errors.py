"""도메인 예외와 통일된 오류 응답({code, message, request_id, errors?}) 형식을 정의한다."""

from collections.abc import Sequence
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from dait.core.logging import request_id_var

MAX_FIELD_ERRORS = 10  # 한 응답에 담는 칸별 오류 수 상한. 큰 요청으로 응답이 커지는 것을 막는다.
INTERNAL_ERROR_MESSAGE = "서버에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요."


class FieldError(BaseModel):
    """입력칸 하나의 오류. 화면이 field 칸 아래에 message를 띄운다. 입력값은 담지 않는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=200)


class ErrorResponse(BaseModel):
    """모든 오류 응답의 공통 본문. errors는 칸별 이유가 있을 때(422 등)만 들어간다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=64)
    errors: list[FieldError] | None = Field(default=None, max_length=MAX_FIELD_ERRORS)


class AppError(Exception):
    """도메인 예외의 부모. 하위 클래스가 상태 코드·코드·공개 메시지를 정한다."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = INTERNAL_ERROR_MESSAGE
    errors: tuple[FieldError, ...] = ()

    def __init__(self) -> None:
        """공개 메시지를 예외 문자열로 쓴다.

        입력: 없음
        출력: 없음
        기능: 내부 원인은 `raise ... from 원인`으로 잇고 메시지에는 담지 않는다.
        """
        super().__init__(self.message)


class NotReadyError(AppError):
    """DB 같은 필수 의존성이 준비되지 않았을 때."""

    status_code = 503
    code = "NOT_READY"
    message = "서비스가 아직 준비되지 않았습니다."


class SignupFailedError(AppError):
    """이미 가입된 이메일로 가입하려 할 때."""

    status_code = 409
    code = "SIGNUP_FAILED"
    # 계정 열거 방지 규칙의 예외: 2026-11-11 사용자 결정(docs/decisions.md). 429 잠금으로 완화.
    message = "이미 가입된 이메일입니다."


_WEAK_MESSAGES = {
    "COMMON_PASSWORD": "너무 흔한 비밀번호입니다.",
    "CONTAINS_EMAIL": "비밀번호에 이메일 앞부분을 쓸 수 없습니다.",
}


class WeakPasswordError(AppError):
    """흔하거나 이메일 앞부분을 포함한 비밀번호로 가입하려 할 때."""

    status_code = 422
    code = "WEAK_PASSWORD"

    def __init__(self, reason: Literal["COMMON_PASSWORD", "CONTAINS_EMAIL"]) -> None:
        """약한 이유에 맞는 문구와 칸별 오류를 싣는다.

        입력: reason (password_policy가 판단한 이유 코드)
        출력: 없음
        기능: 이유마다 문구가 달라 인스턴스 값으로 덮어쓴다. 비밀번호 원문은 담지 않는다.
        """
        self.message = _WEAK_MESSAGES[reason]
        self.errors = (FieldError(field="password", code=reason, message=self.message),)
        super().__init__()


class InvalidCredentialsError(AppError):
    """이메일이 없거나 비밀번호가 틀린 로그인. 두 경우를 구분하지 않는다."""

    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class TooManyAttemptsError(AppError):
    """로그인 실패가 쌓여 일시적으로 잠겼을 때."""

    status_code = 429
    code = "TOO_MANY_ATTEMPTS"
    message = "시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."


class InvalidTwoFactorError(AppError):
    """2차 인증 코드 확인 실패. 틀림·만료·없는 챌린지·시도 초과·이미 사용을 구분하지 않는다."""

    status_code = 401
    code = "INVALID_TWO_FACTOR"
    message = "인증 코드가 올바르지 않거나 만료되었습니다."


class AlreadyLoggedInError(AppError):
    """로그인된 상태에서 가입·로그인을 다시 요청했을 때."""

    status_code = 409
    code = "ALREADY_LOGGED_IN"
    message = "이미 로그인되어 있습니다."


class InvalidTokenError(AppError):
    """토큰이 만료·변조됐거나 형식이 맞지 않을 때."""

    status_code = 401
    code = "INVALID_TOKEN"
    message = "인증 정보가 올바르지 않습니다."


def error_response(
    status_code: int, code: str, message: str, errors: Sequence[FieldError] = ()
) -> Response:
    """통일된 형식의 오류 응답을 만든다.

    입력: status_code (HTTP 상태), code (오류 코드), message (사용자에게 보일 일반 메시지),
          errors (칸별 오류, 없으면 본문에서 빠짐)
    출력: Response (JSON 본문 {code, message, request_id, errors?})
    기능: request_id는 요청 컨텍스트에서 가져온다. 내부 원인은 담지 않는다.
          errors가 없으면 필드 자체를 빼서 기존 {code, message, request_id} 형식을 지킨다.
    """
    body = ErrorResponse(
        code=code,
        message=message,
        request_id=request_id_var.get(),
        errors=list(errors[:MAX_FIELD_ERRORS]) or None,
    )
    return Response(
        content=body.model_dump_json(exclude_none=True),
        status_code=status_code,
        media_type="application/json",
    )


# (칸, Pydantic 오류 종류) 또는 오류 종류만으로 이유 코드와 문구를 찾는다.
_TOO_SHORT = ("TOO_SHORT", "비밀번호는 8자 이상이어야 합니다.")
_TOO_LONG = ("TOO_LONG", "비밀번호는 128자 이하여야 합니다.")
_FIELD_RULES: dict[tuple[str, str] | str, tuple[str, str]] = {
    ("password", "too_short"): _TOO_SHORT,
    ("password", "too_long"): _TOO_LONG,
    ("password_confirm", "too_short"): _TOO_SHORT,
    ("password_confirm", "too_long"): _TOO_LONG,
    "value_error": ("INVALID", "입력 형식이 올바르지 않습니다."),
    "missing": ("REQUIRED", "필수 입력 항목입니다."),
}
# 모델 검증기(ValueError)의 메시지로 구분한다. 위치가 본문 전체라 어느 칸인지도 여기서 정한다.
_MODEL_RULES = {
    "Value error, password mismatch": (
        "password_confirm",
        ("MISMATCH", "비밀번호가 서로 다릅니다."),
    ),
    "Value error, terms not accepted": (
        "terms_accepted",
        ("TERMS_REQUIRED", "이용약관에 동의해 주세요."),
    ),
}
_EMAIL_ERROR = ("INVALID_FORMAT", "올바른 이메일 형식이 아닙니다.")
_DEFAULT_ERROR = ("INVALID", "입력 형식이 올바르지 않습니다.")


def _field_name(loc: Sequence[int | str], error_type: str) -> str:
    """오류 위치에서 화면 칸 이름을 고른다.

    입력: loc (Pydantic 오류 위치, 예: ("body", "password")), error_type (오류 종류)
    출력: str (칸 이름, 고를 수 없으면 "body")
    기능: 알 수 없는 필드 이름은 사용자가 보낸 값이라 그대로 돌려주지 않는다.
    """
    last = loc[-1] if loc else "body"
    if error_type == "extra_forbidden" or not isinstance(last, str):
        return "body"
    return last if last.isidentifier() and len(last) <= 64 else "body"


def to_field_errors(exc: RequestValidationError) -> list[FieldError]:
    """요청 검증 오류를 칸별 오류 목록으로 바꾼다.

    입력: exc (FastAPI 요청 검증 오류)
    출력: list[FieldError] (최대 MAX_FIELD_ERRORS개)
    기능: 오류의 위치·종류·고정 메시지만 쓰고 input·ctx(사용자 입력값)는 버린다.
    """
    result: list[FieldError] = []
    for raw in exc.errors()[:MAX_FIELD_ERRORS]:
        error_type = str(raw.get("type", ""))
        model_rule = _MODEL_RULES.get(str(raw.get("msg", "")))
        if model_rule is not None:
            field, (code, message) = model_rule
        else:
            field = _field_name(tuple(raw.get("loc", ())), error_type)
            if field == "email" and error_type != "missing":
                code, message = _EMAIL_ERROR
            else:
                code, message = _FIELD_RULES.get(
                    (field, error_type), _FIELD_RULES.get(error_type, _DEFAULT_ERROR)
                )
        result.append(FieldError(field=field, code=code, message=message))
    return result


_HTTP_MESSAGES = {
    404: "요청한 경로를 찾을 수 없습니다.",
    405: "허용되지 않는 요청 방식입니다.",
}


async def handle_error(request: Request, exc: Exception) -> Response:
    """FastAPI가 잡은 예외를 통일된 오류 응답으로 바꾼다.

    입력: request (현재 요청, 사용하지 않음), exc (AppError, 검증 오류, HTTP 오류 중 하나)
    출력: Response (오류 응답)
    기능: 검증 오류는 입력값 없이 칸별 이유(errors)와 첫 번째 이유 문구를 낸다.
          알 수 없는 예외는 다시 던진다.
    """
    if isinstance(exc, AppError):
        return error_response(exc.status_code, exc.code, exc.message, exc.errors)
    if isinstance(exc, RequestValidationError):
        errors = to_field_errors(exc)
        message = errors[0].message if errors else _DEFAULT_ERROR[1]
        return error_response(422, "VALIDATION_ERROR", message, errors)
    if isinstance(exc, StarletteHTTPException):
        message = _HTTP_MESSAGES.get(exc.status_code, "요청을 처리할 수 없습니다.")
        return error_response(exc.status_code, f"HTTP_{exc.status_code}", message)
    raise exc


def register_error_handlers(app: FastAPI) -> None:
    """앱에 전역 예외 핸들러를 등록한다.

    입력: app (FastAPI 앱)
    출력: 없음
    기능: 도메인 예외, 요청 검증 오류, HTTP 오류를 모두 같은 핸들러로 보낸다.
    """
    for exc_class in (AppError, RequestValidationError, StarletteHTTPException):
        app.add_exception_handler(exc_class, handle_error)
