"""해외 기사 한국어 결과의 저장 형식과 읽기 전용 조회를 공유합니다."""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from dait.core.config import TRANSLATION_DB
from dait.repositories import result_repository


def input_for(title, description):
    text = json.dumps({"title": title, "rss_description": description}, ensure_ascii=False)
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_result(data):
    if not isinstance(data, dict):
        raise ValueError("번역 결과는 JSON 객체여야 합니다.")
    status, title, lines = data.get("status"), data.get("title_ko"), data.get("lines")
    if status not in ("generated", "insufficient") or not isinstance(title, str) or not title.strip():
        raise ValueError("번역 상태와 한국어 제목을 확인하세요.")
    if any(c in title for c in "\r\n") or not re.search("[가-힣]", title):
        raise ValueError("한국어 제목은 한 줄이어야 하며 한글을 포함해야 합니다.")
    if not isinstance(lines, list):
        raise ValueError("한국어 요약은 문장 배열이어야 합니다.")
    if status == "insufficient":
        if lines:
            raise ValueError("정보 부족 상태의 요약은 빈 배열이어야 합니다.")
    elif (len(lines) != 3 or not all(isinstance(line, str) and line.strip()
          and not any(c in line for c in "\r\n") and re.search("[가-힣]", line) for line in lines)
          or len(set(line.strip() for line in lines)) != 3):
        raise ValueError("서로 다른 한국어 요약 문장 세 개가 필요합니다.")
    return status, title.strip(), [line.strip() for line in lines]


def create_table(db):
    return result_repository.create_table(db)


def latest_record(article_id):
    return result_repository.latest_translation(TRANSLATION_DB, article_id)


def get_translation(article_id, title, description):
    result = {"status": "missing", "title_ko": None, "lines": [],
              "message": "한국어 제목과 요약이 아직 생성되지 않았습니다. 원문 정보를 표시합니다."}
    try:
        row = latest_record(article_id)
    except sqlite3.Error as exc:
        print(f"해외 기사 번역 조회 실패: {exc}")
        return {**result, "status": "unavailable", "message": "한국어 결과를 불러올 수 없습니다. 원문 정보를 표시합니다."}
    if row is None:
        return result
    if row["input_hash"] != input_for(title, description)[1]:
        return {**result, "status": "stale", "message": "원문 정보가 변경되어 한국어 결과를 다시 생성해야 합니다."}
    if row["status"] == "error":
        return {**result, "status": "error", "message": "한국어 제목·요약 생성에 실패했습니다. 원문 정보를 확인해 주세요."}
    try:
        status, title_ko, lines = validate_result({"status": row["status"], "title_ko": row["title_ko"], "lines": json.loads(row["lines_json"])})
    except (ValueError, TypeError):
        return {**result, "status": "invalid", "message": "저장된 한국어 결과의 형식을 확인해야 합니다."}
    note = ("원문 제목을 한국어로 번역했습니다. RSS 설명에 핵심 정보가 부족해 3줄 요약을 만들지 못했습니다."
            if status == "insufficient" else "원문 제목과 RSS 설명을 바탕으로 생성한 한국어 AI 요약입니다. 정확한 내용은 원문을 확인해 주세요.")
    if not row["reviewed"]:
        note += " 검토 전 테스트 결과입니다."
    return {"status": status, "title_ko": title_ko, "lines": lines, "message": note, "model": row["model"]}
