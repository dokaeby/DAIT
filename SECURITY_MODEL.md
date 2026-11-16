# DAIT threat model

DAIT is an AI news curation service: it collects AI-related news from RSS feeds, translates and summarizes it with cloud LLMs, and serves cards, search and personalised feeds to signed-up users, with scheduled searches that can notify users via KakaoTalk "send to me".

Sources: code in `dokaeby/DAIT` (default branch), `README.md`, `HANDOVER.md`, `src/backend/config/.env.example`, and the user's answers (marked **[user]**). No infrastructure-as-code repository exists: Render and Supabase are configured in their dashboards **[user]**.

## System overview and trust boundaries

- **Hosting**: Render web service (`Procfile`: `uvicorn src.server:create_app --factory`), public at `project-dait.onrender.com`, deployed from `origin/main`. Database is Supabase Postgres via `DATABASE_URL` (SQLite locally). Redis (`REDIS_URL`) is configured in production **[user]** for login throttling/cache.
- **Two servers run in production** **[user]**: the integrated API (`src.server` → `dait.main:create_app`) and the legacy news server (`src/backend/app/api/main.py`, collector + LLM pipeline).
- Boundaries: browser ↔ API (public internet); API ↔ DB/Redis (secrets in env); servers ↔ external RSS/article sites (untrusted content, SSRF risk); servers ↔ LLM providers xAI/Groq (API keys, untrusted article text in prompts); external cron (cron-job.org) ↔ `/v1/internal/scheduler/tick` (shared bearer secret); servers ↔ Kakao API (not yet configured: `NotConfiguredSender`).

## Components

| Component | Code |
|---|---|
| Web Client | `src/frontend/public/**`, `src/frontend/src/**` |
| Integrated API | `src/server.py`, `src/backend/src/dait/main.py`, `dait/api/v1/{news,interest,settings}_routes.py`, `dait/core/{middleware,errors,logging}.py`, `dait/schemas/**`, `dait/services/{news_*,interest,settings,ranking_relation,feed_state,source_action}_service.py` |
| Auth & Accounts | `dait/api/deps.py`, `dait/api/v1/{auth,me}_routes.py`, `dait/core/{security,password_policy}.py`, `dait/services/{auth,account,social_auth}_service.py`, `dait/services/login_throttle.py`, `dait/repositories/{user,token}_repository.py` |
| Scheduler & Notifications | `dait/api/v1/scheduler_routes.py`, `dait/services/{schedule,schedule_run,notification_policy}_service.py`, `dait/workers/**` |
| Collection (integrated) | `dait/collectors/**`, `dait/core/url_safety.py`, `dait/services/{collection,robots,pipeline_sync,translation_summary,cache_retry}_service.py` |
| Data Layer | `dait/repositories/**` (other than Auth's), `src/backend/migrations/**`, `src/backend/alembic.ini` |
| Legacy News Server | `src/backend/app/**` (own FastAPI app, RSS collector, content extractor, `workers/cloud_llm.py`, `workers/ai_processor.py`) |
| Config & Dependencies | `dait/core/config.py`, `src/backend/config/.env.example`, `Procfile`, `requirements.txt`, `pyproject.toml`, `uv.lock` |

## Entry points

- Integrated API, anonymous: `/v1/auth/{signup,login,refresh,nickname-availability}`, `GET /v1/news`, `GET /v1/news/{id}`, `/v1/interests/catalog`, `/v1/me/session`, `/healthz`, `/readyz`, `/v1/internal/keepalive`, static files under `/`, `/settings.html`, `/mockup/*`. `/docs` only when `APP_ENV=debug`.
- Integrated API, authenticated (Bearer JWT via `get_current_user`): `/v1/me/*` (nickname, delete account, interests, settings, schedules CRUD, schedule-runs), `/v1/news/activity`, `PUT /v1/news/{id}/read`, `/v1/auth/logout`.
- Internal: `POST /v1/internal/scheduler/tick` (Bearer `SCHEDULER_TICK_SECRET`, `hmac.compare_digest`; disabled when unset).
- Legacy News Server, anonymous: `/`, `/app.js`, `/healthz`, `GET /v1/news`, `GET /v1/news/{id}`, `GET /v1/collection/status`, `/mockup/*`; `POST /v1/news/refresh` gated by `x-refresh-token` == `DAIT_REFRESH_TOKEN` (plain `!=` comparison).
- Indirect: RSS feeds and article pages fetched by collectors; their text flows into the DB, into LLM prompts and onto the Web Client.

## Assets and sensitivity

The user rates all of these as important **[user]**:
- User accounts & credentials: emails, argon2id password hashes, refresh token hashes, access JWTs (stored in browser `localStorage`).
- Server secrets: `JWT_SECRET`, `DATABASE_URL`, `DAIT_XAI_API_KEY`/`DAIT_GROQ_API_KEY`, `SCHEDULER_TICK_SECRET`, `DAIT_REFRESH_TOKEN`, Redis URL.
- Other users' private data: interests, settings, schedules, schedule runs, read history.
- Integrity of the news content shown to users (titles, translations, summaries, links).
- Service availability and API cost: LLM free-tier quota, Render/Supabase capacity, collection loops.

## Attackers

All three are in scope **[user]**:
1. Anonymous internet users hitting either public server.
2. Malicious signed-up users trying to reach other users' data or abuse per-user features (IDOR, schedule abuse, quota exhaustion).
3. Malicious or compromised news sources: crafted RSS/HTML for stored XSS in the Web Client, SSRF via redirects/links, prompt injection into the LLM summaries, oversized/slow responses.

## Existing controls (from code)

- Settings fail fast: `JWT_SECRET` ≥ 32 chars required, `APP_ENV` defaults to `release`, CORS wildcard rejected, docs disabled in release.
- JWT HS256 pinned, required claims; access 15 min; refresh tokens 256-bit random, SHA-256 hashed at rest; argon2id passwords with dummy-hash timing equalisation; login throttling, backed by Redis in production **[user]**; `client_ip` ignores `X-Forwarded-For` (behind Render's proxy this may collapse all clients onto the proxy IP).
- Security headers/CSP via `RequestContextMiddleware`; HTML CSP still allows `'unsafe-inline'` scripts, so any HTML injection in the Web Client is exploitable.
- SSRF guard in `dait/core/url_safety.py` (public HTTPS only, per-hop revalidation, size/time limits); the legacy collectors pin resolved IPs (`copy_with(host=addresses[0])`).
- No automatic migrations or DB reset on start (integrated server); legacy server has `_reset_schema_and_data`, worth checking it cannot be triggered remotely.

## Out of scope / accepted risk

- Every attacker and asset above is in scope, and the legacy news server is production code **[user]**.
- The older code copies under `docs/` (e.g. `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src`) are archive only, never deployed or run: findings there are not worth fixing **[user]**.

## Open questions

- Is Kakao messaging going live soon (OAuth tokens would become a new asset)?
