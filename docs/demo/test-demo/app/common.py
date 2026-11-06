"Shared API-layer types and error helpers."""

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
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("setting fields cannot be null")
        return value

    @field_validator("keywords", "source_ids")
    @classmethod
    def normalize_optional_list(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
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
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("schedule fields cannot be null")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one schedule field is required")
        return self


def error_body(request: Request, code: str, message: str, fields: dict | None = None) -> dict:
    return {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:16]}"),
        "fields": fields,
    }
