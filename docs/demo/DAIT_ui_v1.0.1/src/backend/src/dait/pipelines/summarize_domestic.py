"""국내 기사 전체의 저장된 요약을 점검하고 필요한 기사만 순차 처리합니다."""
from dait.core.config import ensure_runtime_dirs
import argparse
import hashlib
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone

from dait.pipelines.summary_generation import BASE, NEWS_DB, RESULT_DB, create_results_table, generate


def input_for(article):
    text = json.dumps({"title": article["title"], "rss_description": article["summary"]}, ensure_ascii=False)
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def valid_lines(raw):
    try:
        lines = json.loads(raw)
        return (isinstance(lines, list) and len(lines) == 3
                and all(isinstance(line, str) and line.strip() and not any(c in line for c in "\r\n") for line in lines)
                and len(set(line.strip() for line in lines)) == 3)
    except (ValueError, TypeError):
        return False


def plan(model, force=False):
    with closing(sqlite3.connect(NEWS_DB.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        articles = [dict(row) for row in db.execute("SELECT id,title,source,original_url,summary FROM articles WHERE is_foreign=0 ORDER BY published_at DESC,id ASC")]
    previous = {}
    if RESULT_DB.is_file():
        with closing(sqlite3.connect(RESULT_DB.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute("SELECT * FROM summary_tests ORDER BY rowid ASC"):
                previous[row["article_id"]] = dict(row)
    result = []
    for article in articles:
        old = previous.get(article["id"])
        status = old["status"] if old else "missing"
        if old and old["input_hash"] != input_for(article)[1]:
            status = "stale"
        elif status == "generated" and not valid_lines(old["lines_json"]):
            status = "invalid"
        reusable = old and old["model"] == model and status in ("generated", "insufficient")
        result.append((article, status, bool(reusable and not force)))
    return result


def preflight(model):
    # 로컬 API와 설치 모델을 확인해 기사마다 같은 연결 실패를 반복하지 않습니다.
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        data = json.load(response)
    names = {item.get("name") for item in data.get("models", [])}
    if model not in names and model + ":latest" not in names:
        raise ValueError(f"모델을 찾을 수 없습니다. ollama pull {model} 을 실행하세요.")


def main():
    ensure_runtime_dirs()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--timeout", type=int, default=600)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="저장 상태만 확인하며 AI 요청이나 쓰기를 하지 않습니다.")
    mode.add_argument("--list", action="store_true", help="대상 기사와 처리 예정 상태만 확인합니다.")
    parser.add_argument("--force", action="store_true", help="기존 성공·정보 부족 결과도 다시 생성합니다.")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("timeout은 양수여야 합니다.")
    try:
        items = plan(args.model, args.force)
    except (sqlite3.Error, OSError, KeyError) as exc:
        print(f"DB 점검 실패: {exc}", file=sys.stderr)
        return 1
    print(f"국내 기사: {len(items)}개 / 최신 결과 상태: {dict(Counter(status for _, status, _ in items))}")
    pending = [article for article, _, skip in items if not skip]
    print(f"재사용: {len(items) - len(pending)}개 / 처리 대상: {len(pending)}개")
    if args.list:
        for article, status, skip in items:
            print(f"{'재사용' if skip else '처리 예정'} | {status} | {article['id']} | {article['title']}")
    if args.status or args.list or not pending:
        return 0
    if any((article["summary"] or "").strip() for article in pending):
        try:
            preflight(args.model)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            print(f"Ollama 준비 확인 실패: {exc}\nOllama 실행 상태와 모델 설치를 확인하세요. 기사 처리를 시작하지 않았습니다.", file=sys.stderr)
            return 1
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    report_path = BASE / f"domestic_report_{run_id}.txt"
    counts = Counter()
    stopped = False
    with sqlite3.connect(RESULT_DB) as db, report_path.open("w", encoding="utf-8") as report:
        create_results_table(db)
        report.write(f"국내 기사 RSS 기반 요약 | {run_id} | {args.model}\n정확성 검토 전 테스트 결과입니다.\n\n")
        try:
            for index, article in enumerate(pending, 1):
                print(f"[{index}/{len(pending)}] {article['title']}", flush=True)
                start = time.monotonic()
                error, lines = "", []
                try:
                    if not (article["summary"] or "").strip():
                        status = "insufficient"
                    else:
                        status, lines = generate(article, args.model, args.timeout)
                except (OSError, ValueError, TypeError, AttributeError) as exc:
                    status, error = "error", str(exc)
                    # 연결 장애는 나머지 기사에서도 반복될 수 있어 현재 오류 저장 후 중단합니다.
                    stopped = isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))
                elapsed = round(time.monotonic() - start, 2)
                text, input_hash = input_for(article)
                db.execute("INSERT INTO summary_tests (run_id,article_id,model,title,source,original_url,input_text,input_hash,status,lines_json,error,elapsed_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (run_id, article["id"], args.model, article["title"], article["source"], article["original_url"], text, input_hash, status, json.dumps(lines, ensure_ascii=False), error, elapsed))
                db.commit()
                counts[status] += 1
                report.write(f"ID: {article['id']}\n{article['title']}\n{article['original_url']}\n[RSS 입력]\n{article['summary']}\n[AI 결과] {status} / {elapsed}초\n")
                for n, line in enumerate(lines, 1):
                    report.write(f"{n}. {line}\n")
                report.write(error + "\n\n")
                report.flush()
                print(f"  {status} / {elapsed}초" + (f" / {error}" if error else ""), flush=True)
                if stopped:
                    print("연결 장애로 중단했습니다. 완료된 결과는 보존됩니다.")
                    break
        except KeyboardInterrupt:
            stopped = True
            print("중단했습니다. 완료된 결과는 보존됩니다.")
        remaining = len(pending) - sum(counts.values())
        report.write(f"이번 실행: {dict(counts)} / 미처리: {remaining}개\n")
    print(f"이번 실행: {dict(counts)} / 미처리: {remaining}개\n보고서: {report_path}\n결과 DB: {RESULT_DB}")
    return 1 if stopped or counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
