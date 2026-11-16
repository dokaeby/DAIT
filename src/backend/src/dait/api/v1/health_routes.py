"""/healthz(프로세스 생존), /readyz(DB·Redis 준비), /v1/internal/keepalive 라우트.

버전 접두사 없이 루트에 두되 keepalive만 /v1/internal 하위에 둔다.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from dait.core.config import Settings, get_settings
from dait.schemas.health import HealthResponse, KeepAliveResponse
from dait.services.health_service import ensure_database_ready, ensure_redis_ready

router = APIRouter(tags=["health"])


# 입력: 없음.
# 출력: 프로세스 생존 상태 응답.
# 동작: 외부 의존성을 조회하지 않고 즉시 정상 상태를 반환한다.
# def(동기)로 선언해야 sqlite 호출이 FastAPI 스레드풀에서 돌아 이벤트 루프를 막지 않는다.
@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """프로세스가 살아 있는지 알려 준다.

    입력: 없음
    출력: HealthResponse ({"status": "ok"})
    기능: 의존성은 확인하지 않고 즉시 응답한다.
    """
    return HealthResponse(status="ok")


# 입력: 의존성으로 주입된 앱 설정.
# 출력: DB와 선택적 Redis의 준비 상태 응답.
# 동작: 필수 저장소가 응답하지 않으면 503 도메인 오류를 발생시킨다.
@router.get("/readyz", response_model=HealthResponse)
def readyz(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """요청을 받을 준비가 됐는지(DB 연결) 알려 준다.

    입력: settings (의존성으로 주입되는 앱 설정)
    출력: HealthResponse ({"status": "ready"})
    기능: DB가 응답하지 않거나 Redis가 설정됐는데 연결되지 않으면
          503 NOT_READY 오류 형식으로 나간다.
    """
    ensure_database_ready(settings.database_url)
    ensure_redis_ready(settings)
    return HealthResponse(status="ready")


@router.get("/v1/internal/keepalive", response_model=KeepAliveResponse, include_in_schema=False)
def keepalive(response: Response) -> KeepAliveResponse:
    """외부 cron의 keep-alive ping 전용. DB·Redis를 거치지 않고 즉시 200을 반환한다.

    입력: 없음 (인증 불필요 — 공개 정보만 반환)
    출력: KeepAliveResponse ({"status":"ok","service":"dait","time":...})
    기능: Render Free 스핀다운(15분 무요청)을 막기 위해 cron-job.org 등이
          10분 간격으로 호출한다. 어떤 의존성 장애가 있어도 서버를 깨우는
          역할은 유지해야 하므로 readiness 검사를 하지 않는다.
          매 호출이 새로운 서버 시각을 반환하도록 캐시를 금지한다.
    """
    response.headers["Cache-Control"] = "no-store"
    return KeepAliveResponse(time=datetime.now(UTC).isoformat())
