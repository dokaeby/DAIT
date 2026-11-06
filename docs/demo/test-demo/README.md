# DAIT 로컬 데모

`docs/DAIT_v1.0.1_docs`의 화면·API·DB 설계를 기준으로 만든 독립 실행형 MVP입니다. 메인, 뉴스 상세, 설정 화면이 FastAPI와 SQLite를 통해 실제로 동작합니다.

## 구현 범위

- 메인: 뉴스 목록, 제목·요약 검색, 랭킹순·최신순 정렬
- 상세: 3줄 요약, 번역, 처리 정보, 관련 뉴스, 원문 열기·링크 복사
- 설정: 키워드·출처·노출 수·알림 저장, 예약 조회·생성·활성 전환·삭제
- API: `/v1/news`, `/v1/news/{id}`, `/v1/me/settings`, `/v1/me/schedules`
- DB: 설계서의 13개 테이블과 FK·CHECK·UNIQUE 제약
- 사용자: `usr_demo_local` / `demo@dait.local` 고정 로컬 사용자

외부 뉴스 수집, LLM 처리, 로그인, Redis, 알림 전송은 포함하지 않습니다. 앱을 처음 실행하면 화면 확인용 데이터가 멱등하게 생성됩니다.

## 요구 환경

- Python 3.12
- `uv` 권장 (`pip`도 사용 가능)

### 일반 Linux/macOS

```bash
cd docs/demo/test-demo
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
```

### WSL에서 저장소가 `/mnt/c` 아래에 있는 경우

일부 Python/AnyIO 조합은 Windows 마운트 안의 가상환경에서 작업 스레드가 정지할 수 있습니다. 가상환경만 Linux 파일시스템에 만드세요.

```bash
cd docs/demo/test-demo
uv venv --python 3.12 /tmp/dait-test-demo-venv
UV_CACHE_DIR=/tmp/dait-uv-cache uv pip install --python /tmp/dait-test-demo-venv/bin/python -r requirements.txt
PYTHONPATH=. /tmp/dait-test-demo-venv/bin/uvicorn app.main:app --reload
```

## 화면 주소

- 메인: <http://127.0.0.1:8000/>
- 상세: <http://127.0.0.1:8000/detail.html?id=news_openai_001>
- 설정: <http://127.0.0.1:8000/settings.html>
- API 문서: <http://127.0.0.1:8000/docs>

## SQLite

기본 DB 파일은 `data/dait.db`입니다. 다른 위치를 사용하려면 실행 전에 `DAIT_DB_PATH`를 지정합니다.

```bash
DAIT_DB_PATH=/tmp/dait.db PYTHONPATH=. /tmp/dait-test-demo-venv/bin/uvicorn app.main:app
```

로컬 샘플 DB만 초기화하려면 서버를 종료한 뒤 `data/dait.db`를 삭제하고 다시 실행합니다. 소스 파일이나 다른 프로젝트 데이터에는 영향을 주지 않습니다.

## 테스트

일반 환경:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests -q
```

WSL `/mnt/c` 환경:

```bash
PYTHONPATH=. /tmp/dait-test-demo-venv/bin/python -m pytest tests -q
```

JavaScript 구문 검사:

```bash
node --check public/app.js
```

## 구조

```text
test-demo/
├── app/
│   ├── common.py     # 공통 API 요청 모델과 오류 응답
│   ├── database.py   # 13개 테이블, 시드, SQLite 조회·저장
│   └── main.py       # FastAPI 엔드포인트와 정적 화면 제공
├── data/             # 실행 시 dait.db 생성
├── public/
│   ├── index.html
│   ├── detail.html
│   ├── settings.html
│   ├── styles.css
│   └── app.js
├── tests/
├── requirements.txt
└── README.md
```
