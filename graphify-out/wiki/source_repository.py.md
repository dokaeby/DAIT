# source_repository.py

> 13 nodes

## Key Concepts

- **source_repository.py** (9 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **SourceRow** (6 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **list_enabled()** (5 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **touch_robots_checked()** (5 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **get_by_id()** (4 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **DbConnection** (3 connections)
- **datetime** (2 connections)
- **NamedTuple** (1 connections)
- **sources 테이블 접근. 수집 대상은 enabled=1인 승인 출처뿐이다.** (1 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **활성화된 출처를 우선순위 순으로 읽는다. 입력: conn (연결) 출력: SourceRow 목록 기능: 수집기는 이 목록만 대상으로 하므로…** (1 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **출처 한 건을 읽는다(수동 수집 지정용). 입력: conn (연결), source_id (sources.id) 출력: SourceRow 또는…** (1 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **robots 확인 시각을 갱신한다. 입력: conn (연결), source_id, now (UTC 시각) 출력: 없음 기능: 다음 수집 주기의…** (1 connections) — `src/backend/src/dait/repositories/source_repository.py`
- **ambiguous_python_import_a8d0b55b1853** (1 connections)

## Relationships

- [collection_service.py](collection_service.py.md) (5 shared connections)
- [typing](typing.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/source_repository.py`

## Audit Trail

- EXTRACTED: 23 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*