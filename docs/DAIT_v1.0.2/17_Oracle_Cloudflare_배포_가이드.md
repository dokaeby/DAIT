# DAIT 배포 설치 가이드 (Oracle Always Free + Supabase + Cloudflare Tunnel)

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.2 |
| 기준일 | 2026-11-11 |
| 목적 | Render 무료 티어의 스핀다운 없이 DAIT 웹앱을 영구 무료 조합(Oracle Cloud Always Free VM + Supabase PostgreSQL + Cloudflare Tunnel)으로 호스팅하는 절차를 정리한다 |
| 대상 | `src/backend`(FastAPI + 정적 프론트엔드), `src/frontend/public`, 선택적 `src/backend/app` 파이프라인 |
| 관련 문서 | 02 시스템상세설계서 5.3/15절, 06 API설계서 7.3절, 15 PostgreSQL/SQLite 전환 가이드, 16 배포 설치 가이드(Render 기준) |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.2 | seonghoon.yang | 2026-11-11 | Oracle Always Free + Supabase + Cloudflare Tunnel 무료 배포 가이드 신규 작성 |

## 1. 전체 구성

```text
사용자 브라우저
    │ HTTPS (도메인)
    ▼
Cloudflare ── Tunnel(cloudflared) ──▶ Oracle VM (private, 공개 포트 불필요)
                                          │
                                          ├── systemd: uvicorn dait.main:app :8000
                                          ├── (선택) systemd: uvicorn app.api.main:app :8001
                                          ├── (선택) Redis (로컬 또는 Upstash)
                                          └── DATABASE_URL ──▶ Supabase PostgreSQL

cron-job.org ── HTTPS ──▶ Cloudflare ──▶ POST /v1/internal/scheduler/tick
```

- **Oracle Cloud Always Free**: Ampere ARM VM(최대 4 OCPU/24GB) 영구 무료. 스핀다운 없음.
- **Supabase**: PostgreSQL DB. 연결 문자열만 사용.
- **Cloudflare Tunnel**: VM에 공개 포트를 열지 않고 HTTPS로 외부 노출. TLS·DDoS 방어 자동.
- **cron-job.org**: 예약 tick 트리거(기존과 동일).

## 2. 사전 준비

- GitHub 저장소 push 완료 (`develop` 브랜치)
- 도메인(선택): Cloudflare에 등록된 도메인이 있으면 `dait.example.com` 같은 서브도메인 사용. 없으면 `trycloudflare.com` 임시 URL로 시작 가능(단, 임시 URL은 재시작 시 변경됨)
- Supabase 프로젝트 생성
- Oracle Cloud 계정(Always Free)

## 3. Supabase 설정

Render 절차와 동일하다(16번 문서 3절 참고). 요약:

1. 프로젝트 생성 → Settings → Database → Connection string 복사
2. **Session pooler** URI 사용 권장: `postgresql://dait_app:PASS@aws-0-<region>.pooler.supabase.com:5432/postgres`
   - VM 아웃바운드는 IPv4이므로 Supabase의 IPv6 전용 직결 주소 대신 pooler 사용
3. SQL Editor에서 전용 역할 생성:

```sql
CREATE ROLE dait_app LOGIN PASSWORD '<강한 비밀번호>';
GRANT CONNECT ON DATABASE postgres TO dait_app;
```

4. 마이그레이션 후 테이블 권한 부여(4.4절 이후):

```sql
GRANT USAGE ON SCHEMA public TO dait_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dait_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dait_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dait_app;
```

## 4. Oracle Cloud VM 구성

### 4.1 인스턴스 생성

1. cloud.oracle.com → Compute → Instances → Create instance
2. 설정:
   - **Image**: Ubuntu 24.04 (aarch64)
   - **Shape**: VM.Standard.A1.Flex — 1 OCPU / 6GB부터 시작(Always Free 한도 내 조정 가능, 최대 4/24)
   - **SSH 키**: 본인 공개키 등록
   - **부트 볼륨**: 50GB(Always Free 한도) — Ubuntu + 앱 + Redis 충분
3. 생성 후 공인 IP 확인(있으면 기록, 없어도 Tunnel 사용 시 불필요)

### 4.2 기본 패키지

```bash
ssh ubuntu@<VM_PUBLIC_IP>
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip git curl \
    build-essential libpq-dev
```

> Ubuntu 24.04 기본 Python이 3.12 미만이면 `deadsnakes` PPA 또는 `uv`로 해결한다.
> `uv` 사용을 권장: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 4.3 저장소 클론

```bash
mkdir -p ~/dait && cd ~/dait
git clone https://github.com/dokaeby/DAIT.git repo
cd repo
```

## 5. 앱 배포

### 5.1 환경 파일

`src/backend/config/.env` 생성(저장소에 커밋 금지):

```bash
cd ~/dait/repo/src/backend/config
cp .env.example .env
```

`.env`에 설정:

```env
APP_ENV=release
DATABASE_URL=postgresql://dait_app:<PASS>@aws-0-<region>.pooler.supabase.com:5432/postgres
JWT_SECRET=<openssl rand -hex 32 출력값>
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30
CORS_ORIGINS=["https://dait.example.com"]
SCHEDULER_TICK_SECRET=<아직 미구현 — 예약>
# 클라우드 LLM(선택)
DAIT_GROQ_API_KEY=
DAIT_XAI_API_KEY=
# 파이프라인 앱(선택)
DAIT_DATABASE_URL=sqlite:///./dait.db
DAIT_REDIS_HOST=127.0.0.1
```

주의:
- `DATABASE_URL`이 `postgresql://`이면 저장소 계층이 자동으로 psycopg 백엔드를 선택한다(15번 전환 가이드).
- `src/backend/app` 파이프라인은 `DAIT_DATABASE_URL`을 별도로 읽는다. 같은 Supabase를 쓰려면 `DAIT_DATABASE_URL=postgresql+asyncpg://...` 형태로 지정하고 `asyncpg` 설치 필요 여부를 확인한다.

### 5.2 의존성 설치와 마이그레이션

```bash
cd ~/dait/repo
uv sync --frozen          # 또는: python3.12 -m venv .venv && .venv/bin/pip install -e .
cd src/backend
export $(grep -v '^#' config/.env | xargs)   # 또는 systemd EnvironmentFile 사용
../../.venv/bin/alembic upgrade head
```

> `.env`를 systemd `EnvironmentFile`로 넘기는 방식이 더 안전하다(5.3절).

### 5.3 systemd 서비스 (권장)

`/etc/systemd/system/dait.service`:

```ini
[Unit]
Description=DAIT API server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dait/repo/src/backend
EnvironmentFile=/home/ubuntu/dait/repo/src/backend/config/.env
Environment=PYTHONPATH=/home/ubuntu/dait/repo/src/backend/src
ExecStart=/home/ubuntu/dait/repo/.venv/bin/uvicorn --factory dait.main:create_app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dait
curl http://127.0.0.1:8000/healthz   # {"status":"ok"}
curl http://127.0.0.1:8000/readyz    # {"status":"ready"}
```

(선택) `src/backend/app` 파이프라인을 함께 띄우려면 `dait-pipeline.service`를 :8001로 동일하게 추가하고, `DAIT_ENABLE_LIVE_RSS` 등 해당 앱의 환경변수를 `.env`에 병기한다.

### 5.4 배포 갱신 절차

```bash
cd ~/dait/repo
git pull
uv sync --frozen
cd src/backend && ../../.venv/bin/alembic upgrade head
sudo systemctl restart dait
```

(선택) GitHub Actions로 pull+restart 자동화 가능 — `workflow_dispatch` 또는 push 트리거.

## 6. Cloudflare Tunnel 설정

### 6.1 cloudflared 설치

```bash
# 저장소의 cloudflared 설치 스크립트 대신 배포판 패키지 권장
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare.gpg] https://pkg.cloudflare.com/cloudflared noble main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared
cloudflared --version
```

### 6.2 Named Tunnel 생성

```bash
cloudflared tunnel login        # 브라우저 인증 → 도메인의 Zone 선택
cloudflared tunnel create dait  # tunnel UUID 출력, 자격증명 JSON 생성됨
```

`/etc/cloudflared/config.yml` (`/root/.cloudflared/` 또는 `~/.cloudflared/` 기준):

```yaml
credentials-file: /home/ubuntu/.cloudflared/<UUID>.json
ingress:
  - hostname: dait.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

DNS 라우팅 + 서비스 등록:

```bash
cloudflared tunnel route dns dait dait.example.com
sudo cloudflared service install   # systemd 등록
sudo systemctl enable --now cloudflared
```

도메인이 없으면 임시 URL:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
# 출력된 https://xxx.trycloudflare.com 으로 접속 가능(재시작 시 URL 변경)
```

### 6.3 확인

- `https://dait.example.com/` → 메인 페이지
- `https://dait.example.com/healthz` → `{"status":"ok"}`
- `https://dait.example.com/readyz` → `{"status":"ready"}`

## 7. Redis (선택)

`REDIS_URL`을 설정하지 않으면 `cache_retry_service`가 인메모리 fallback으로 동작한다 — 단일 VM에서는 인메모리로 충분하다.

외부 Redis가 필요하면 Upstash 무료 티어(`rediss://...`)를 `REDIS_URL`에 지정한다.

## 8. cron-job.org (예약 tick)

16번 문서 5절과 동일. tick 엔드포인트 구현 후:

- URL: `https://dait.example.com/v1/internal/scheduler/tick`
- Method: POST
- Header: `Authorization: Bearer <SCHEDULER_TICK_SECRET>`
- 주기: 5~15분

VM은 상시 실행이므로 콜드스타트 없이 즉시 처리된다 — Render 무료 대비 이 조합의 핵심 장점.

## 9. 배포 체크리스트

- [ ] Supabase 프로젝트 + `dait_app` 역할 + pooler URI
- [ ] Oracle VM 생성(A1.Flex, Ubuntu 24.04 aarch64, 50GB)
- [ ] `src/backend/config/.env` 작성(git 커밋 금지 확인)
- [ ] `alembic upgrade head` → Supabase에 테이블 생성
- [ ] Supabase SQL Editor에서 `dait_app` 테이블 권한 부여
- [ ] `dait.service` systemd 등록·기동 → `/healthz`, `/readyz` 200
- [ ] `cloudflared` 설치·Named Tunnel·DNS·systemd 등록
- [ ] `https://도메인/` 접속 확인
- [ ] 회원가입→로그인→뉴스 목록→설정 저장 수동 확인
- [ ] (선택) 파이프라인 앱 :8001 + Redis
- [ ] (선택) cron-job.org tick 등록(tick 엔드포인트 구현 후)

## 10. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `/readyz` 503 | DB 연결 실패 | `DATABASE_URL` pooler URI·비밀번호·`dait_app` 권한 확인. `psql`로 직접 접속 테스트 |
| `ValidationError` on startup | `JWT_SECRET` 32자 미만 | `openssl rand -hex 32`로 재생성 |
| 알 수 없는 스킴 오류 | `DATABASE_URL`에 `postgres://` 외 값 | `postgresql://` 또는 `postgresql+psycopg://`만 허용 |
| 마이그레이션이 sqlite에 적용됨 | `env.py`가 로컬 URL 사용 | `DATABASE_URL`을 export한 상태에서 alembic 실행 |
| Tunnel은 되는데 API 502 | `dait.service` 다운 또는 :8000 미수신 | `systemctl status dait`, `curl 127.0.0.1:8000/healthz` |
| Supabase 연결 타임아웃 | 직결 IPv6 주소 사용 | 반드시 **pooler** URI 사용 |
| cron tick 404 | 엔드포인트 미구현 | 06 API설계서 7.3절 구현 후 등록 |
| `dait_app` 권한 오류 | GRANT 미실행 | 3절 SQL 재실행, `ALTER DEFAULT PRIVILEGES` 포함 |

## 11. Render 대비 장단점 정리

| 항목 | Oracle+Tunnel+Supabase | Render+Supabase |
|---|---|---|
| 비용 | 완전 무료(Always Free) | 무료 티어(750h/월) |
| 스핀다운 | 없음 | 15분 무요청 시 발생(콜드스타트 ~50s) |
| 백그라운드 worker | 가능(같은 VM에 추가 systemd) | 불가(웹 프로세스 내 통합 필요) |
| Redis | VM 로컬 또는 Upstash | Upstash 등 외부 필요 |
| 운영 부담 | VM 패치·모니터링 직접 | PaaS가 관리 |
| 도메인/TLS | Cloudflare가 자동 처리 | Render가 자동 처리 |
