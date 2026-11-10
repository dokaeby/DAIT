"""FR-SET-01~03 설정 API: /v1/me/settings 와 /v1/me/schedules.

모든 경로는 인증 필수이며 사용자 ID는 토큰에서만 얻는다(IDOR 방지).
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from dait.api.deps import get_current_user
from dait.core.config import Settings, get_settings
from dait.core.logging import request_id_var
from dait.schemas.settings import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from dait.schemas.user import UserRecord
from dait.services import schedule_service, settings_service

router = APIRouter(prefix="/v1/me", tags=["settings"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("/settings", response_model=SettingsResponse, summary="내 설정 조회")
def get_my_settings(settings: SettingsDep, user: CurrentUser) -> SettingsResponse:
    """관심 키워드·승인 출처·카테고리·노출 수·알림 설정을 조회한다.

    입력: settings, user (Bearer 토큰으로 확인된 본인)
    출력: SettingsResponse (없으면 기본값 생성 후 반환)
    기능: 토큰이 없으면 401.
    """
    return settings_service.get_settings(settings, user)


@router.patch("/settings", response_model=SettingsResponse, summary="내 설정 저장")
def update_my_settings(
    body: SettingsUpdateRequest, settings: SettingsDep, user: CurrentUser
) -> SettingsResponse:
    """설정을 부분 수정하고 서버가 정규화한 저장 값을 돌려준다.

    입력: body (보낸 필드만 변경), settings, user (본인)
    출력: SettingsResponse
    기능: 미승인 출처·비활성 카테고리·형식 오류는 422.
    """
    return settings_service.update_settings(
        settings, user, body, request_id_var.get(), datetime.now(UTC)
    )


@router.get("/schedules", response_model=ScheduleListResponse, summary="예약 목록")
def list_my_schedules(settings: SettingsDep, user: CurrentUser) -> ScheduleListResponse:
    """본인의 예약 목록을 조회한다."""
    return schedule_service.list_schedules(settings, user)


@router.post(
    "/schedules",
    response_model=ScheduleResponse,
    status_code=201,
    summary="예약 생성",
)
def create_my_schedule(
    body: ScheduleCreateRequest, settings: SettingsDep, user: CurrentUser
) -> ScheduleResponse:
    """예약을 만들고 다음 실행 시각(UTC)을 계산해 저장한다.

    입력: body (local_time HH:mm, IANA timezone, enabled, criteria)
    출력: ScheduleResponse (201)
    기능: 잘못된 시간대·미승인 출처·예약 상한 초과는 422.
    """
    return schedule_service.create_schedule(
        settings, user, body, request_id_var.get(), datetime.now(UTC)
    )


@router.patch(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    summary="예약 수정",
)
def update_my_schedule(
    schedule_id: str,
    body: ScheduleUpdateRequest,
    settings: SettingsDep,
    user: CurrentUser,
) -> ScheduleResponse:
    """본인의 예약을 부분 수정하고 변경된 전체 객체를 돌려준다.

    입력: schedule_id (경로), body (보낸 필드만 변경), settings, user
    출력: ScheduleResponse
    기능: 타인 예약은 404 SCHEDULE_NOT_FOUND로 존재 여부를 숨긴다.
    """
    return schedule_service.update_schedule(
        settings, user, schedule_id, body, request_id_var.get(), datetime.now(UTC)
    )


@router.delete(
    "/schedules/{schedule_id}",
    status_code=204,
    summary="예약 삭제",
)
def delete_my_schedule(
    schedule_id: str,
    settings: SettingsDep,
    user: CurrentUser,
) -> Response:
    """본인의 예약을 삭제하고 감사 로그를 남긴다.

    입력: schedule_id (경로), settings, user
    출력: 204 (본문 없음)
    기능: 타인 예약은 404.
    """
    schedule_service.delete_schedule(
        settings, user, schedule_id, request_id_var.get(), datetime.now(UTC)
    )
    return Response(status_code=204)
