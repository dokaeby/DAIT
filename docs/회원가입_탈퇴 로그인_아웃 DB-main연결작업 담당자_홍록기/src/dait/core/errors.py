"""도메인 예외와 통일된 오류 응답({code, message, request_id}) 형식을 정의한다."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from dait.core.logging import request_id_var


class ErrorResponse(BaseModel):
    """모든 오류 응답의 공통 본문."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=64)


class AppError(Exception):
    """도메인 예외의 부모. 하위 클래스가 상태 코드·코드·공개 메시지를 정한다."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "서버 내부 오류가 발생했습니다."

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
    """가입을 마무리하지 못했을 때(이미 쓰는 이메일 포함). 이유를 구체적으로 알려 주지 않는다."""

    status_code = 409
    code = "SIGNUP_FAILED"
    message = "가입을 완료할 수 없습니다. 입력 내용을 확인해 주세요."


class WeakPasswordError(AppError):
    """흔하거나 이메일을 포함한 비밀번호로 가입하려 할 때."""

    status_code = 422
    code = "WEAK_PASSWORD"
    message = "너무 흔한 비밀번호입니다. 다른 비밀번호를 사용해 주세요."


class InvalidCredentialsError(AppError):
    """이메일이 없거나 비밀번호가 틀린 로그인. 두 경우를 구분하지 않는다."""

    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class TooManyAttemptsError(AppError):
    """로그인 실패가 쌓여 일시적으로 잠겼을 때."""

    status_code = 429
    code = "TOO_MANY_ATTEMPTS"
    message = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."


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


def error_response(status_code: int, code: str, message: str) -> Response:
    """통일된 형식의 오류 응답을 만든다.

    입력: status_code (HTTP 상태), code (오류 코드), message (사용자에게 보일 일반 메시지)
    출력: Response (JSON 본문 {code, message, request_id})
    기능: request_id는 요청 컨텍스트에서 가져온다. 내부 원인은 담지 않는다.
    """
    body = ErrorResponse(code=code, message=message, request_id=request_id_var.get())
    return Response(
        content=body.model_dump_json(), status_code=status_code, media_type="application/json"
    )


_HTTP_MESSAGES = {
    404: "요청한 경로를 찾을 수 없습니다.",
    405: "허용되지 않는 요청 방식입니다.",
}


async def handle_error(request: Request, exc: Exception) -> Response:
    """FastAPI가 잡은 예외를 통일된 오류 응답으로 바꾼다.

    입력: request (현재 요청, 사용하지 않음), exc (AppError, 검증 오류, HTTP 오류 중 하나)
    출력: Response (오류 응답)
    기능: 검증 오류는 입력값 없이 422 일반 메시지만 낸다. 알 수 없는 예외는 다시 던진다.
    """
    if isinstance(exc, AppError):
        return error_response(exc.status_code, exc.code, exc.message)
    if isinstance(exc, RequestValidationError):
        return error_response(422, "VALIDATION_ERROR", "요청 형식이 올바르지 않습니다.")
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
