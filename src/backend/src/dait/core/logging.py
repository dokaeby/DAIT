"""로깅 설정과 민감정보 마스킹을 담당한다. 로그 모드 분기는 여기서만 한다."""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

from dait.core.config import AppEnv, Settings

# 요청마다 task가 따로 생기므로 값이 다른 요청으로 새지 않는다.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_HANDLER_NAME = "dait"
AUDIT_LOGGER_NAME = "dait.audit"
_BEARER = re.compile(r"(?i)bearer\s+[\w\-.~+/]+=*")
# "키: 값" 또는 "키=값" 형태만 가린다(JSON 따옴표 포함). 문장 속 일반 단어는 건드리지 않는다.
_SECRET_PAIR = re.compile(
    r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|authorization)"
    r"([\"']?\s*[:=]\s*[\"']?)[^\s\"',}&]+"
)
_EMAIL = re.compile(r"([\w.+-])[\w.+-]*@([\w-]+(?:\.[\w-]+)+)")


# 입력: 로그에 기록하려는 문자열.
# 출력: 인증정보·비밀번호·이메일이 가려진 문자열.
# 동작: 알려진 민감정보 패턴을 로그에 남기기 전에 치환한다.
def mask_sensitive(text: str) -> str:
    """로그 문자열에서 토큰, 비밀번호류 값, 이메일을 가린다.

    입력: text (로그 메시지 문자열)
    출력: str (민감정보가 *** 로 바뀐 문자열)
    기능: Bearer 토큰, password/token/secret 등의 값, 이메일 앞부분을 가린다.
    """
    masked = _BEARER.sub("Bearer ***", text)
    masked = _SECRET_PAIR.sub(r"\1\2***", masked)
    return _EMAIL.sub(r"\1***@\2", masked)


class MaskingFilter(logging.Filter):
    """모든 로그 레코드에 마스킹을 적용하고 request_id를 붙이는 필터."""

    # 입력: logging이 만든 로그 레코드.
    # 출력: 항상 참인 로그 통과 여부.
    # 동작: 완성된 메시지를 마스킹하고 현재 request_id를 붙인다.
    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드의 메시지를 마스킹하고 request_id를 달아 통과시킨다.

        입력: record (logging이 만든 로그 레코드)
        출력: bool (항상 True, 로그를 버리지 않음)
        기능: 인자 치환을 끝낸 뒤 마스킹해야 인자로 들어온 비밀값도 가려진다.
        """
        record.msg = mask_sensitive(record.getMessage())
        record.args = None
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """한 줄 JSON으로 로그를 만드는 포매터. 예외는 종류 이름만 남긴다."""

    # 입력: 마스킹을 마친 로그 레코드.
    # 출력: 한 줄 JSON 로그 문자열.
    # 동작: 공개 가능한 필드와 예외 종류만 구조화해 직렬화한다.
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 문자열 한 줄로 바꾼다.

        입력: record (MaskingFilter를 통과한 로그 레코드)
        출력: str (time, level, logger, request_id, message 키를 가진 JSON)
        기능: 스택트레이스는 개인정보가 섞일 수 있어 예외 클래스 이름만 error 키에 넣는다.
        """
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["error"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)


# 입력: 검증된 앱 설정.
# 출력: 반환값 없음.
# 동작: 실행 모드에 맞는 로그 수준·형식·민감정보 필터를 설정한다.
def configure_logging(settings: Settings) -> None:
    """실행 모드에 맞춰 루트 로거를 설정한다.

    입력: settings (검증된 앱 설정)
    출력: 없음(루트 로거와 uvicorn 로거 설정이 바뀜)
    기능: release는 WARNING 이상 JSON, debug는 DEBUG 이상 일반 형식.
          여러 번 불러도 핸들러는 하나만 유지한다.
    """
    release = settings.app_env is AppEnv.RELEASE
    level = logging.WARNING if release else logging.DEBUG
    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(_HANDLER_NAME)
    handler.addFilter(MaskingFilter())
    handler.setFormatter(
        JsonFormatter()
        if release
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
    )
    root = logging.getLogger()
    for old in [h for h in root.handlers if h.get_name() == _HANDLER_NAME]:
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(level)
    # uvicorn이 자체 INFO 로그(접속 기록 등)를 내므로 같은 수준으로 맞춘다.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(level)
    # 감사 로그는 release(WARNING 이상)에서도 남아야 하므로 이 로거만 INFO로 연다.
    logging.getLogger(AUDIT_LOGGER_NAME).setLevel(logging.INFO)


# 입력: 보안 이벤트, 처리 결과, 선택적 사용자 ID와 클라이언트 IP.
# 출력: 반환값 없음.
# 동작: 비밀번호·토큰·이메일 없이 인증 관련 감사 로그를 남긴다.
def audit(
    event: str, outcome: str, user_id: str | None = None, client_ip: str | None = None
) -> None:
    """보안 이벤트를 감사 로그 한 줄로 남긴다.

    입력: event (예: signup, login), outcome (success 또는 failure 사유 코드),
          user_id (알면 사용자 id), client_ip (요청 IP)
    출력: 없음
    기능: 누가/언제/무엇을만 남긴다. 비밀번호·토큰·이메일은 받지도 않아 기록될 수 없다.
    """
    logging.getLogger(AUDIT_LOGGER_NAME).info(
        "audit event=%s outcome=%s user_id=%s ip=%s",
        event,
        outcome,
        user_id or "-",
        client_ip or "-",
    )
