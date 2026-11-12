"""/healthz(프로세스 생존)와 /readyz(DB 준비) 라우트. 버전 접두사 없이 루트에 둔다."""

from typing import Annotated

from fastapi import APIRouter, Depends

from dait.core.config import Settings, get_settings
from dait.schemas.health import HealthResponse
from dait.services.health_service import ensure_database_ready, ensure_redis_ready

router = APIRouter(tags=["health"])


# def(동기)로 선언해야 sqlite 호출이 FastAPI 스레드풀에서 돌아 이벤트 루프를 막지 않는다.
@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """프로세스가 살아 있는지 알려 준다.

    입력: 없음
    출력: HealthResponse ({"status": "ok"})
    기능: 의존성은 확인하지 않고 즉시 응답한다.
    """
    return HealthResponse(status="ok")


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
