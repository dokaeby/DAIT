"""요청마다 request_id 부여, 본문 크기 제한, 보안 헤더 추가, 미처리 예외 일반화를 한다."""

import logging
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from dait.core.errors import error_response
from dait.core.logging import request_id_var

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_048_576  # 1MiB. 이 파트의 JSON 요청은 훨씬 작아서 넉넉한 상한이다.
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """모든 요청/응답에 공통 처리를 적용하는 미들웨어."""

    # 입력: 감쌀 ASGI 앱과 일반·HTML 응답의 CSP 값.
    # 출력: 요청 공통 처리 미들웨어.
    # 동작: 설정 계층에서 결정된 보안 헤더 값을 저장한다.
    def __init__(self, app: ASGIApp, csp: str, html_csp: str | None = None) -> None:
        """미들웨어를 만든다.

        입력: app (감쌀 ASGI 앱), csp (응답에 붙일 Content-Security-Policy 값)
        출력: 없음
        기능: CSP 값은 모드에 따라 core/config가 정해 주므로 여기서는 모드를 보지 않는다.
        """
        super().__init__(app)
        self._csp = csp
        self._html_csp = html_csp

    # 입력: 현재 HTTP 요청과 다음 처리 단계.
    # 출력: request_id와 보안 헤더가 포함된 HTTP 응답.
    # 동작: 요청 크기·ID를 검증하고 미처리 예외의 내부 정보를 숨긴다.
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """요청을 처리하고 응답에 request_id와 보안 헤더를 붙인다.

        입력: request (들어온 요청), call_next (다음 처리 단계)
        출력: Response (헤더가 보강된 응답)
        기능: X-Request-ID는 영문·숫자·- 64자 이하일 때만 받고 아니면 새로 만든다(로그 위조 방지).
              Content-Length가 1MiB를 넘으면 413, 처리 중 예외는 일반 500으로 바꾸고
              원인은 로그에만 남긴다.
        """
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
        request_id_var.set(request_id)  # 되돌리지 않는다: 예외 핸들러가 같은 task에서 읽어야 한다.

        length = request.headers.get("content-length", "0")
        if not length.isdigit():
            response = error_response(400, "BAD_REQUEST", "요청 형식이 올바르지 않습니다.")
        elif int(length) > MAX_BODY_BYTES:
            response = error_response(413, "PAYLOAD_TOO_LARGE", "요청 본문이 너무 큽니다.")
        else:
            try:
                response = await call_next(request)
            except Exception:  # 마지막 방어선: 어떤 예외도 내부 정보 없이 500으로만 나가게 한다.
                logger.exception("처리되지 않은 오류")
                response = error_response(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다.")

        response.headers["X-Request-ID"] = request_id
        is_html = response.headers.get("content-type", "").startswith("text/html")
        response.headers["Content-Security-Policy"] = (
            self._html_csp if is_html and self._html_csp else self._csp
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"] = "DENY"
        return response
