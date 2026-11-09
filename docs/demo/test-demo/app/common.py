"Shared API-layer types and error helpers."

from __future__ import annotations

import uuid
from typing import Literal, Self

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criteria(StrictModel):
    keywords: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    categories: list[Literal["AI"]]

    @field_validator("keywords", "source_ids")
    @classmethod
    # 입력: `values`.
    # 출력: `list[str]` 값.
    # 동작: 문자열 목록의 공백을 제거하고 입력 순서를 유지하며 중복을 제거한다.
    def normalize_list(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class SettingsPatch(StrictModel):
    default_count: Literal[5, 10] | None = None
    keywords: list[str] | None = None
    source_ids: list[str] | None = None
    categories: list[Literal["AI"]] | None = None
    in_app_notice: bool | None = None
    email_notice: bool | None = None

    @field_validator(
        "default_count",
        "keywords",
        "source_ids",
        "categories",
        "in_app_notice",
        "email_notice",
        mode="before",
    )
    @classmethod
    # 입력: `value`.
    # 출력: `object` 값.
    # 동작: 명시적으로 전달된 null 값을 검증 오류로 거부한다.
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("setting fields cannot be null")
        return value

    @field_validator("keywords", "source_ids")
    @classmethod
    # 입력: `values`.
    # 출력: `list[str] | None` 값.
    # 동작: 선택 문자열 목록이 있으면 공백과 중복을 정규화한다.
    def normalize_optional_list(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
    # 입력: 없음.
    # 출력: `Self` 값.
    # 동작: 부분 변경 모델에 하나 이상의 변경 필드가 있는지 검증한다.
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one setting is required")
        return self


class ScheduleCreate(StrictModel):
    local_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: Literal["Asia/Seoul"]
    enabled: bool = True
    criteria: Criteria


class SchedulePatch(StrictModel):
    local_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: Literal["Asia/Seoul"] | None = None
    enabled: bool | None = None
    criteria: Criteria | None = None

    @field_validator("local_time", "timezone", "enabled", "criteria", mode="before")
    @classmethod
    # 입력: `value`.
    # 출력: `object` 값.
    # 동작: 명시적으로 전달된 null 값을 검증 오류로 거부한다.
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("schedule fields cannot be null")
        return value

    @model_validator(mode="after")
    # 입력: 없음.
    # 출력: `Self` 값.
    # 동작: 부분 변경 모델에 하나 이상의 변경 필드가 있는지 검증한다.
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one schedule field is required")
        return self


# 입력: `request`, `code`, `message`, `fields`.
# 출력: `dict` 값.
# 동작: 공통 오류 코드, 메시지, 요청 ID와 필드 오류를 응답 본문으로 구성한다.
def error_body(request: Request, code: str, message: str, fields: dict | None = None) -> dict:
    return {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:16]}"),
        "fields": fields,
    }
