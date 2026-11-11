"""DAIT 최신 뉴스와 테스트 사용자별 추천 화면."""
import html
import hashlib
import json
import secrets
import sys
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie, CookieError
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from dait.services.foreign_content import get_translation
from dait.services import search_lab_service
from dait.services import summary_service
from frontend.views import render_main, render_detail, summary_status

from dait.core.config import NEWS_DB as DB, SUMMARY_DB, ASSETS_DIR
from dait.repositories import news_repository

KST = timezone(timedelta(hours=9))
USERS = {"user1": ("인공지능",), "user2": ("보안", "클라우드"), "user3": ("반도체",)}
TEST_PASSWORD = "1234"


def normalize_query(raw):
    query = " ".join(raw.split())
    if len(query) > 200:
        raise ValueError("검색어는 200자 이하여야 합니다.")
    return query


def filter_articles(articles, query, category=""):
    if category:
        articles = [a for a in articles if category in (a[4] or "").split(" · ")]
    terms = normalize_query(query).casefold().split()
    if not terms:
        return articles[:10]
    matches = []
    for article in articles:
        article_id, title, _, _, _, is_foreign, description = article
        translated_title = ""
        if is_foreign:
            translated_title = get_translation(article_id, title, description)["title_ko"] or ""
        text = "\n".join((title or "", description or "", translated_title)).casefold()
        if all(term in text for term in terms):
            matches.append(article)
            if len(matches) == 10:
                break
    return matches


def latest_articles(query="", category=""):
    articles = news_repository.latest_rows(DB, -1 if query or category else 10)
    return filter_articles(articles, query, category)


def recommended_articles(user, query="", category="", interests=None):
    interests = USERS.get(user, ()) if interests is None else tuple(interests)
    if not interests:
        return latest_articles(query, category)
    articles = news_repository.recommended_rows(DB, interests, -1 if query or category else 10)
    return filter_articles(articles, query, category)


def get_article(article_id):
    return news_repository.get_article(DB, article_id)


def get_ai_summary(article_id, article):
    result = {"status": "missing", "lines": [], "message": "아직 AI 요약이 생성되지 않은 기사입니다."}
    if not SUMMARY_DB.is_file():
        return result
    try:
        row = news_repository.summary_record(SUMMARY_DB, article_id)
    except sqlite3.Error as exc:
        print(f"AI 요약 DB 조회 실패: {exc}")
        return {**result, "status": "unavailable", "message": "AI 요약을 불러올 수 없습니다."}
    if row is None:
        return result
    status, lines_json, input_hash, model, reviewed = row
    input_text = json.dumps({"title": article[0], "rss_description": article[3]}, ensure_ascii=False)
    if hashlib.sha256(input_text.encode("utf-8")).hexdigest() != input_hash:
        return {**result, "status": "stale", "message": "기사 정보가 변경되어 AI 요약을 다시 생성해야 합니다."}
    if status == "insufficient":
        return {**result, "status": status, "message": "제공된 기사 정보가 부족해 3줄 요약을 만들지 못했습니다."}
    if status == "error":
        return {**result, "status": status, "message": "AI 요약 생성에 실패했습니다. 원문 또는 아래 기사 설명을 확인해 주세요."}
    try:
        lines = json.loads(lines_json)
        valid = (status == "generated" and isinstance(lines, list) and len(lines) == 3
                 and all(isinstance(line, str) and line.strip() and not any(c in line for c in "\r\n") for line in lines))
        if not valid or len(set(line.strip() for line in lines)) != 3:
            raise ValueError("요약 형식 오류")
    except (ValueError, TypeError):
        return {**result, "status": "invalid", "message": "저장된 AI 요약의 형식을 확인해야 합니다."}
    note = "RSS 설명을 바탕으로 생성한 AI 요약입니다. 정확한 내용은 원문을 확인해 주세요."
    if not reviewed:
        note += " 검토 전 테스트 결과입니다."
    return {"status": "generated", "lines": [line.strip() for line in lines], "message": note, "model": model}


def get_saved_summary(article_id, title, description, is_foreign=False):
    """메인·상세·팝업에서 동일한 저장 결과만 읽습니다. 생성 요청은 하지 않습니다."""
    summary = (get_translation(article_id, title, description) if is_foreign
               else get_ai_summary(article_id, (title, None, None, description)))
    can_retry = False
    if summary["status"] not in ("generated", "insufficient"):
        try:
            job = summary_service.worker.article_state(article_id, title, description, is_foreign)
        except sqlite3.Error:
            job = None
        if job:
            state = job["state"]
            if state in ("queued", "running", "retry", "failed"):
                summary = {**summary, "status": state, "lines": [], "message": job["message"]}
                can_retry = state == "failed" and not is_foreign
    tone, label = summary_status(summary)
    return {**summary, "status_tone": tone, "status_label": label, "can_retry": can_retry}


def display_date(raw):
    try:
        date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if date.tzinfo is None:
            return raw
        return date.astimezone(KST).strftime("%Y.%m.%d %H:%M") + " KST"
    except ValueError:
        return raw


def page(articles, user=None, query="", scores=None, category="", sort="rank", interests=None, nickname=None, fallback=False, prefs=None):
    urls = {}
    try:
        urls = news_repository.original_urls(DB)
    except sqlite3.Error:
        pass
    if prefs is not None:
        # KAN-10: 설정의 기본 노출 수를 메인 목록에 적용합니다.
        articles = articles[:prefs.display_count]
    cards = []
    for article_id, title, source, published, categories, foreign, description in articles:
        summary = get_saved_summary(article_id, title, description, foreign)
        cards.append(dict(id=article_id, title=(summary.get("title_ko") or title), source=source,
                          date=display_date(published), categories=categories, foreign=foreign,
                          url=urls.get(article_id), summary=summary))
    selected = USERS.get(user, ()) if interests is None else tuple(interests)
    categories = list(selected) if user and selected else available_categories()
    if prefs is not None:
        # KAN-10: 설정한 카테고리 순서를 따르고 숨긴 카테고리는 칩에서 뺍니다(선택 중인 칩은 유지).
        rank = {name: index for index, name in enumerate(prefs.category_order)}
        hidden = set(prefs.hidden_categories)
        categories = sorted((c for c in categories if c not in hidden or c == category),
                            key=lambda c: (rank.get(c, len(rank)), categories.index(c)))
    return render_main(cards, user, query, scores, selected, category, sort, categories, nickname, fallback, prefs=prefs)


def available_categories():
    return news_repository.categories(DB)


def detail_page(article, user, ai_summary, translation=None):
    return render_detail(article, user, ai_summary, translation, display_date(article[2]))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        result = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def current_user(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            value = cookie["dait_user"].value if "dait_user" in cookie else None
            return value if value in USERS else None
        except CookieError:
            return None

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/assets/"):
            filename = path[len("/assets/"):]
            if filename not in ("design.css", "app.css", "app.js", "detail.js"):
                self.send_error(404)
                return
            asset = ASSETS_DIR / filename
            result = asset.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8" if filename.endswith(".css") else "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(result)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(result)
            return
        if path == "/api/search-lab/info":
            user = self.current_user()
            self.send_json({"user": user, "interests": USERS.get(user, []), "model": search_lab_service.MODEL,
                            "index_exists": search_lab_service.INDEX_DB.is_file()})
            return
        if path.startswith("/api/search-lab/jobs/"):
            job = search_lab_service.get(path.rsplit("/", 1)[-1], self.current_user())
            self.send_json(job or {"error": "작업을 찾을 수 없습니다. 현재 계정을 확인해 주세요."}, 200 if job else 404)
            return
        if path.startswith("/api/summary/jobs/"):
            job = summary_service.get(path.rsplit("/", 1)[-1])
            self.send_json(job or {"error": "작업을 찾을 수 없습니다."}, 200 if job else 404)
            return
        if path == "/api/summary/batch-status":
            self.send_json(summary_service.batch_status())
            return
        if path != "/" and not path.startswith("/article/"):
            self.send_error(404)
            return
        try:
            user = self.current_user()
            if path == "/":
                try:
                    params = parse_qs(urlsplit(self.path).query)
                    query = normalize_query(params.get("q", [""])[0])
                    category = params.get("category", [""])[0][:40]
                    sort = "latest" if params.get("sort") == ["latest"] else "rank"
                except ValueError:
                    self.send_error(400, "Search query too long")
                    return
                job_id = params.get("search_job", [""])[0]
                if job_id:
                    job = search_lab_service.get(job_id, user)
                    data = job.get("result") if job and job["status"] == "completed" else None
                    if not data or data.get("query") != query or data.get("user") != (user or "비로그인") or data.get("category", "") != category:
                        self.send_error(404, "Search result unavailable")
                        return
                    rows, scores = [], {}
                    for item in data["hybrid"]:
                        article = get_article(item["id"])
                        if article is not None:
                            rows.append((item["id"], article[0], article[1], article[2], article[7], article[6], article[3]))
                            scores[item["id"]] = item["cosine"]
                    if sort == "latest":
                        rows.sort(key=lambda row: row[3], reverse=True)
                    result = page(rows, user, query, scores, category, sort).encode("utf-8")
                else:
                    result = page(recommended_articles(user, query, category) if user else latest_articles(query, category), user, query, category=category, sort=sort).encode("utf-8")
            else:
                article_id = unquote(path[len("/article/"):])
                article = get_article(article_id)
                if article is None:
                    self.send_error(404, "Article not found", "해당 기사를 찾을 수 없습니다.")
                    return
                ai_summary = get_saved_summary(article_id, article[0], article[3], article[6])
                translation = ai_summary if article[6] else None
                if parse_qs(urlsplit(self.path).query).get("format") == ["json"]:
                    title, source, published, summary, content, original_url, is_foreign, categories = article
                    url = urlsplit(original_url or "")
                    safe_url = original_url if url.scheme in ("http", "https") and url.netloc else None
                    display_title = translation["title_ko"] if translation and translation["title_ko"] else title
                    foreign_notice = ("해외 기사 · AI 번역 제목과 원문 RSS 설명을 함께 제공합니다." if translation and translation["title_ko"]
                                      else "해외 기사 · 한국어 결과가 준비되지 않아 원문 제목과 설명을 표시합니다." if is_foreign else "")
                    result = json.dumps({"title": display_title, "original_title": title, "foreign_notice": foreign_notice,
                                         "source": source, "published_at": display_date(published),
                                         "description": summary or content or "", "original_url": safe_url,
                                         "is_foreign": bool(is_foreign), "categories": categories,
                                         "ai_summary": ai_summary}, ensure_ascii=False).encode("utf-8")
                else:
                    result = detail_page(article, user, ai_summary, translation).encode("utf-8")
        except (sqlite3.Error, OSError) as exc:
            print(f"DB 조회 실패: {exc}")
            self.send_error(500, "Database unavailable")
            return
        self.send_response(200)
        is_json = path.startswith("/article/") and parse_qs(urlsplit(self.path).query).get("format") == ["json"]
        self.send_header("Content-Type", ("application/json" if is_json else "text/html") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/summary/batch":
            try:
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise ValueError("JSON 요청이 필요합니다.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("요청 크기를 확인하세요.")
                json.loads(self.rfile.read(length).decode("utf-8"))
                self.send_json({"job_id": summary_service.start_batch()}, 202)
            except (ValueError, TypeError, UnicodeError) as exc:
                self.send_json({"error": str(exc)}, 400)
            except RuntimeError as exc:
                self.send_json({"error": str(exc)}, 409)
            return
        if path == "/api/summary/jobs":
            try:
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise ValueError("JSON 요청이 필요합니다.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("요청 크기를 확인하세요.")
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                article_path = data.get("article_path", "") if isinstance(data, dict) else ""
                if not isinstance(article_path, str) or not article_path.startswith("/article/"):
                    raise ValueError("기사 주소를 확인하세요.")
                article_id = unquote(article_path[len("/article/"):])
                article = get_article(article_id)
                if article is None:
                    raise ValueError("기사를 찾을 수 없습니다.")
                job_id = summary_service.start(article_id, article)
                self.send_json({"job_id": job_id}, 202)
            except (ValueError, TypeError, UnicodeError, sqlite3.Error, OSError) as exc:
                self.send_json({"error": str(exc)}, 400)
            except RuntimeError as exc:
                self.send_json({"error": str(exc)}, 409)
            return
        if path == "/api/search-lab/jobs":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("요청 크기를 확인하세요.")
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("요청 형식을 확인하세요.")
                query = normalize_query(str(data.get("query", "")))
                category = str(data.get("category", ""))[:40]
                job_id = search_lab_service.start(data.get("action"), query, float(data.get("min_score", 0.35)), self.current_user(), category)
                self.send_json({"job_id": job_id}, 202)
            except (ValueError, TypeError, UnicodeError) as exc:
                self.send_json({"error": str(exc)}, 400)
            except RuntimeError as exc:
                self.send_json({"error": str(exc)}, 409)
            return
        if path not in ("/login", "/logout"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 8192:
                raise ValueError()
            fields = parse_qs(self.rfile.read(length).decode("utf-8"))
            query = normalize_query(fields.get("q", [""])[0]) if path == "/login" else ""
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        user = fields.get("user", [""])[0] if path == "/login" else ""
        password = fields.get("password", [""])[0] if path == "/login" else ""
        if path == "/login" and (user not in USERS or not secrets.compare_digest(password.encode("utf-8"), TEST_PASSWORD.encode("utf-8"))):
            self.send_json({"error": "아이디 또는 비밀번호가 올바르지 않습니다."}, 401)
            return
        if path == "/login" and self.current_user() == user:
            self.send_json({"error": "이미 로그인되어 있습니다."}, 409)
            return
        if path == "/login" and self.current_user() is None:
            query = ""
        self.send_response(303)
        self.send_header("Location", "/?" + urlencode({"q": query}) if query else "/")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", f"dait_user={user}; Path=/; HttpOnly; SameSite=Lax" + ("; Max-Age=0" if not user else ""))
        self.end_headers()


if __name__ == "__main__":
    # 비교 모듈이 이 앱의 설정을 읽을 때 이미 로드된 모듈을 재사용합니다.
    import sys
    sys.modules.setdefault("app", sys.modules[__name__])
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("DAIT 실행 중: http://127.0.0.1:8000 (종료: Ctrl+C)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
