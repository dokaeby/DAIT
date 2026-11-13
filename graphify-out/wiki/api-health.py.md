# api/health.py

> 14 nodes

## Key Concepts

- **api/health.py** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **readyz()** (7 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **healthz()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **get** (2 connections)
- **HealthResponse** (2 connections)
- **Depends** (1 connections)
- **get_settings** (1 connections)
- **Settings** (1 connections)
- **/healthz(프로세스 생존)와 /readyz(DB 준비) 라우트. 버전 접두사 없이 루트에 둔다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **프로세스가 살아 있는지 알려 준다. 입력: 없음 출력: HealthResponse ({"status": "ok"}) 기능: 의존성은 확인하지…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **요청을 받을 준비가 됐는지(DB 연결) 알려 준다. 입력: settings (의존성으로 주입되는 앱 설정) 출력: HealthResponse…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`
- **ambiguous_python_import_5daceb048eef** (1 connections)
- **ambiguous_python_import_ca5de469762c** (1 connections)
- **ambiguous_python_import_e795bb3e9c24** (1 connections)

## Relationships

- [typing](typing.md) (2 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/main.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-main.py.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/api/health.py`

## Audit Trail

- EXTRACTED: 18 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*