"""Immutable contracts for AI content processing (AI/ECONOMY/SOCIETY categories, Korean MVP)."""

import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from src.backend.app.core.taxonomy import CategoryType

SENTENCE_ERROR = "Each summary line must contain exactly one complete sentence"
RESULT_ERROR = "Result fields do not match the processing status"
TEXT_ERROR = "Text must not be blank"
_ABBREVIATIONS = re.compile(r"\b(?:U\.S\.|U\.K\.|e\.g\.|i\.e\.|Dr\.|Mr\.|Ms\.|Prof\.)", re.I)


class ContentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentPolicy(ContentModel):
    """Version changes invalidate cached results. No API credentials belong here."""

    category: CategoryType = "AI"
    target_language: Literal["ko"] = "ko"
    model_version: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    prompt_version: str = Field(default="v1", pattern=r"^[\w.-]+$")
    privacy_version: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    min_body_chars: int = Field(default=100, ge=1)
    max_body_chars: int = Field(default=50000, ge=100)
    timeout_seconds: float = Field(default=30, gt=0, le=300, allow_inf_nan=False)
    cache_ttl_seconds: int = Field(default=86400, ge=1)

    @model_validator(mode="after")
    def validate_limits(self) -> Self:
        if self.min_body_chars > self.max_body_chars:
            raise ValueError(RESULT_ERROR)
        return self


class PrivacyDecision(ContentModel):
    """A deployment-supplied local privacy scanner must explicitly approve transfer.

    The scanner must remove personal names and other identifiers according to its
    policy. Regex redaction alone is not a complete privacy assessment.
    protected_terms contains only approved non-personal names, e.g. organizations.
    """

    approved: bool
    sanitized_text: str = Field(max_length=50000)
    protected_terms: tuple[str, ...] = ()


class LLMRequest(ContentModel):
    system_instruction: str
    untrusted_text: str = Field(min_length=1, max_length=50000)
    category: CategoryType = "AI"
    target_language: Literal["ko"] = "ko"
    model_version: str
    tools_enabled: Literal[False] = False


class GeneratedContent(ContentModel):
    summary_lines: tuple[str, str, str]
    translated_text: str = Field(min_length=1, max_length=100000)

    @field_validator("summary_lines")
    @classmethod
    def validate_sentences(cls, lines: tuple[str, str, str]) -> tuple[str, str, str]:
        if len(lines) != 3:
            raise ValueError(SENTENCE_ERROR)
        cleaned: list[str] = []
        for original in lines:
            if any(
                character in original
                for character in ("\n", "\r", "\v", "\f", "\x85", "\u2028", "\u2029")
            ):
                raise ValueError(SENTENCE_ERROR)
            line = original.strip()
            protected = _ABBREVIATIONS.sub("ABBR", line)
            protected = re.sub(r"(?<=\d)\.(?=\d)", "DECIMAL", protected)
            endings = tuple(re.finditer(r"[.!?。\uff01\uff1f]+", protected))
            if (
                not line
                or len(line) > 2000
                or len(endings) != 1
                or not re.fullmatch(
                    r"""[.!?。\uff01\uff1f]+["'\u2019”)]*""", protected[endings[0].start() :]
                )
                or not re.search(r"\w", protected[: endings[0].start()])
            ):
                raise ValueError(SENTENCE_ERROR)
            cleaned.append(line)
        return cleaned[0], cleaned[1], cleaned[2]

    @field_validator("translated_text")
    @classmethod
    def nonblank(cls, text: str) -> str:
        if not text.strip():
            raise ValueError(TEXT_ERROR)
        return text.strip()


class SuccessContent(GeneratedContent):
    status: Literal["SUCCESS"] = "SUCCESS"
    category: CategoryType = "AI"
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    engine: str = Field(default="", max_length=50)
    model_id: str = Field(default="", max_length=200)
    prompt_version: str = Field(default="", max_length=50)


class InsufficientContent(ContentModel):
    status: Literal["INSUFFICIENT"] = "INSUFFICIENT"
    category: CategoryType = "AI"
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_lines: tuple[()] = ()
    translated_text: None = None
    engine: str = Field(default="", max_length=50)
    model_id: str = Field(default="", max_length=200)
    prompt_version: str = Field(default="", max_length=50)


type ContentResult = Annotated[SuccessContent | InsufficientContent, Field(discriminator="status")]
CONTENT_RESULT_ADAPTER = TypeAdapter(ContentResult)
