# health_routes.py

> 17 nodes

## Key Concepts

- **health_routes.py** (11 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **readyz()** (7 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **keepalive()** (5 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **healthz()** (4 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **get** (3 connections)
- **HealthResponse** (2 connections)
- **Depends** (1 connections)
- **get_settings** (1 connections)
- **Response** (1 connections)
- **Settings** (1 connections)
- **/healthz(프로세스 생존), /readyz(DB·Redis 준비), /v1/internal/keepalive 라우트. 버전 접두사 없이…** (1 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **프로세스가 살아 있는지 알려 준다. 입력: 없음 출력: HealthResponse ({"status": "ok"}) 기능: 의존성은 확인하지…** (1 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **요청을 받을 준비가 됐는지(DB 연결) 알려 준다. 입력: settings (의존성으로 주입되는 앱 설정) 출력: HealthResponse…** (1 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **외부 cron의 keep-alive ping 전용. DB·Redis를 거치지 않고 즉시 200을 반환한다. 입력: 없음 (인증 불필요 — 공개…** (1 connections) — `src/backend/src/dait/api/v1/health_routes.py`
- **ambiguous_python_import_289d5c313d17** (1 connections)
- **ambiguous_python_import_391234f89e2d** (1 connections)
- **ambiguous_python_import_d55c8c9d5cdc** (1 connections)

## Relationships

- [typing](typing.md) (2 shared connections)
- [backend/src/dait/schemas/health.py](backend-src-dait-schemas-health.py.md) (1 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [src/backend/src/dait/main.py](src-backend-src-dait-main.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/health_routes.py`

## Audit Trail

- EXTRACTED: 24 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*