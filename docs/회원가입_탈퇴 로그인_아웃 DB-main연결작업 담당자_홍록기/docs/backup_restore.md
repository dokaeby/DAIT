# DB 백업·복구 절차 (회원 파트, sqlite)

AGENTS.md 8절 6번: "DB 백업과 복구 절차를 문서화하고, 복구가 실제로 되는지 확인한다."

대상은 `DATABASE_URL`이 가리키는 sqlite 파일 하나다(기본 `./dait.db`). 안에 `users`, `refresh_tokens`,
`user_interests`, `alembic_version`이 들어 있다. 운영 DB를 PostgreSQL(Supabase)로 옮기면 이 문서는
그쪽 백업 도구(pg_dump, Supabase 백업)로 대체해야 한다.

## 백업

서버가 켜져 있어도 일관된 사본을 만드는 sqlite 온라인 백업을 쓴다. 파일을 그냥 복사하면 쓰는 도중의
상태가 섞일 수 있어서 서버를 끈 상태가 아니면 권하지 않는다.

```powershell
python -c "import sqlite3,sys; a=sqlite3.connect(sys.argv[1]); b=sqlite3.connect(sys.argv[2]); a.backup(b); b.close(); a.close()" dait.db backups/dait-2026-11-08.db
```

- 백업 파일에는 비밀번호 해시와 refresh 토큰 해시, 이메일이 들어 있으므로 개인정보와 같이 다룬다.
  Git에 올리지 않는다(`*.db`는 `.gitignore`에 있다). 접근 권한이 있는 곳에만 보관한다.
- 권장 주기: 시연 전, 마이그레이션 적용 전, 하루 한 번. 오래된 사본은 보관 기간(예: 14일)이 지나면 삭제한다.
- 탈퇴한 사용자는 실제로 삭제되므로, 백업에 남아 있는 사본에도 개인정보가 있다. 보관 기간을 짧게 두고
  복구 후에는 탈퇴 처리된 사용자를 다시 지우는 절차가 필요하다(아래 "복구 후 확인").

## 복구

1. 서버를 멈춘다(SIGTERM 또는 Ctrl+C).
2. 망가진 DB 파일을 다른 이름으로 옮겨 둔다(원인 조사용).
3. 백업 파일을 `DATABASE_URL`이 가리키는 경로에 같은 이름으로 복사한다.

```powershell
Move-Item dait.db dait.broken.db
Copy-Item backups/dait-2026-11-08.db dait.db
```

4. 서버를 다시 시작한다.

## 복구 후 확인 (반드시)

1. 무결성: `PRAGMA integrity_check`가 `ok`여야 한다.
2. 마이그레이션 버전: `alembic current`가 최신 head(현재 `0002_interests`)와 같아야 한다.
   더 오래된 백업이면 `alembic upgrade head`로 올린다.
3. 행 수: `users`, `user_interests`, `refresh_tokens`의 개수가 백업 시점과 맞는지 본다.
4. 실제 로그인: 알려진 계정으로 로그인해 토큰과 관심사가 내려오는지 본다.
5. 백업 시점 이후 탈퇴한 사용자가 되살아났을 수 있다. 탈퇴 요청 기록(감사 로그의 `withdraw success`)과
   대조해 해당 사용자를 다시 삭제한다.
6. refresh 토큰은 복구 시점 기준으로 유효하다. 보안 사고로 복구한 경우에는 `refresh_tokens` 테이블을
   비워 모든 사용자를 다시 로그인시키고, 필요하면 `JWT_SECRET`도 교체한다(`key_rotation.md`).

## 복구 훈련 기록

- 2026-11-08: 임시 DB(사용자 1, 관심사 2, 토큰 2)를 온라인 백업 → 원본 삭제 → 백업 복사 →
  `integrity_check` ok → 행 수 일치(1/2/2) → `alembic current`가 `0002_interests (head)` →
  복구된 DB로 실제 로그인 성공, 관심사 `ai.models`, `economy.jobs` 확인. 운영 데이터가 아니라
  이 폴더의 임시 DB로 한 훈련이다.
