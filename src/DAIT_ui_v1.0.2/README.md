# 현재 구조 안내

현재 백엔드 코드는 `src/dait/`, 화면 코드는 `src/frontend/`, 기존 `backend.*` 호환 코드는 `src/backend/`에 있습니다. `docs/STRUCTURE.md`와 이식 기록은 이전 구조를 설명할 수 있으므로 아래 구조를 기준으로 확인하세요. 구조 변경 전후 단위 테스트 결과는 모두 115개 통과, 12개 실패였습니다. 실패 항목은 별도 확인이 필요합니다.

# DAIT — AI 뉴스 큐레이션 서비스

DAIT는 여러 출처의 뉴스를 모아 **AI 3줄 요약으로 핵심을 빠르게 읽고, 관심 분야와 의미 검색으로 필요한 기사를 찾는 서비스**입니다.

뉴스 원문을 하나씩 열어보는 수고를 줄이고, 같은 기사의 요약을 모든 사용자가 함께 재사용하는 것을 목표로 개발했습니다. 현재는 Windows에서 실행하는 기능 검증용 프로젝트이며, 운영 배포를 위한 인증·보안·품질 기준을 모두 충족한 상태는 아닙니다.

> 백엔드 패키지 전환 후에는 기존 가상환경에서도 `python -m pip install -e . --no-deps`를 한 번 실행합니다. 서버 진입점은 `dait.main:app`이며 기존 `backend.main:app`도 호환됩니다. 호환 코드 이동 후에는 편집 가능 설치를 다시 실행합니다.

> 문서 기준일: 2026-11-09 / Asia/Seoul. 현재 실행 방법은 이 README를 우선합니다. `docs/history/`는 과거 단계별 기록입니다.

## 1. 무엇을 할 수 있나요?

| 기능 | 현재 동작 |
|---|---|
| 비로그인 메인 | 최신 뉴스 최대 10건과 저장된 AI 요약 표시 |
| 회원가입·로그인 | 아이디·비밀번호 가입, 회원 DB 저장, 로그인·계정 전환·로그아웃 |
| 관심 뉴스 | 회원별 관심 카테고리 선택·저장과 맞춤 목록 |
| 통합 검색 | 키워드와 임베딩 의미 검색을 결합하고 카드에 실제 유사도 표시 |
| AI 3줄 요약 | 수집된 기사 중 필요한 기사만 백그라운드에서 순차 처리 |
| 뉴스 상세 | 메인 위 팝업, 원문 링크, 기사 설명, 저장 요약·처리 상태 |
| 자동 갱신 | 메인 상태 갱신, 열린 팝업의 미완료 요약 상태 갱신 |
| 설정 화면 | 로그인 회원 전용 화면. 관심사 전용 기능 외의 설정 저장·예약·알림 등은 미연결 |

**현재 요약 입력은 기사 전문이 아니라 RSS에서 제공한 제목과 설명입니다.** 설명이 부족하면 요약을 임의로 채우지 않고 `정보 부족`으로 처리합니다. 해외 기사는 한국어 제목과 RSS 기반 한국어 요약을 만들며, 기사 전문 번역은 제공하지 않습니다. 생성된 세 문장은 형식 검사를 거친 결과이며, 사실 검증 완료를 뜻하지 않습니다.

## 2. 두 모델은 역할이 다릅니다

| 구분 | AI 요약·한국어 제목 | 의미 검색 |
|---|---|---|
| 모델 | `qwen3:4b` | `intfloat/multilingual-e5-small` |
| 실행 도구 | Ollama | Python의 Sentence Transformers |
| 역할 | 기사 정보를 문장으로 요약·번역 | 검색어와 기사 정보를 벡터로 바꾸어 유사도 계산 |
| 연결 | 로컬 Ollama API, 포트 11434 | Python 프로세스에서 CPU 실행 |
| 설치 | `ollama pull qwen3:4b` | Python 의존성 설치 후 최초 사용 시 다운로드 |

임베딩 모델은 Ollama에 설치하지 않습니다. 현재 기본 모델은 E5-small이며, 이전 기록에 있는 `BAAI/bge-m3`를 추가 설치할 필요는 없습니다. E5 검색어에는 `query:`, 기사에는 `passage:` 접두사를 코드에서 적용합니다. [모델 공식 안내](https://huggingface.co/intfloat/multilingual-e5-small)

검색 유사도는 -1~1 범위의 코사인 값입니다. 정확도나 관련성 확률이 아니므로 0.7을 70% 정확도로 해석하면 안 됩니다. 관련 없는 입력의 결과를 충분히 걸러내는 정책은 추가 검토 대상입니다.

## 3. 데이터는 어떻게 처리되나요?

```text
공개 RSS 수집 → 기사 DB 저장 → 요약이 필요한 기사 등록
                              ↓
                   공통 대기열에서 한 기사씩 AI 처리
                              ↓
                     요약·한국어 결과 DB 저장
                              ↓
               비로그인 메인 / 맞춤 메인 / 상세 팝업

검색어 → 키워드 검색 + E5 임베딩 검색 → 결합 순위와 유사도 표시
```

- 같은 입력·모델의 정상 요약과 정보 부족 판정은 재사용합니다.
- FastAPI 서버가 실행 중이면 약 10초 간격으로 기사 DB를 확인합니다. 서버를 꺼둔 동안 수집한 기사는 다음 서버 시작 시 확인합니다.
- 기사별 첫 실패 후 60초, 두 번째 실패 후 300초 간격으로 최대 3회 시도합니다. 앞선 작업이 있으면 실제 처리 시점은 더 늦어집니다.
- CPU 환경에서 요약은 오래 걸릴 수 있습니다. 한 요청의 최대 대기 시간은 현재 600초입니다.
- 최종 실패한 국내 기사는 상세 팝업의 **요약 다시 시도**로 우선 대기열에 넣을 수 있습니다. 이미 생성 중인 기사는 먼저 끝납니다.
- 브라우저를 열거나 계정을 바꾸는 행위로 같은 기사를 새로 요약하지 않습니다.

## 4. 처음 설치하기 — Windows PowerShell

### 4-1. 준비물과 프로젝트 위치

1. Python 3.12 이상을 설치합니다. [Python 공식 다운로드](https://www.python.org/downloads/windows/)
2. Git으로 저장소를 받거나 ZIP을 내려받아 압축을 풉니다.
3. **`pyproject.toml`, `src`, `requirements.txt`가 함께 있는 프로젝트 루트 폴더**에서 터미널을 엽니다.

이 PC의 실제 프로젝트 경로는 아래와 같습니다. 다른 PC에서는 자신의 다운로드 위치로 바꿉니다.

```powershell
cd C:\workspace\DAIT_ui_relocation_test
py --version
```

`py`를 찾지 못하면 설치된 Python의 `python --version`을 확인하고, 아래의 `py -m venv` 대신 `python -m venv`를 사용합니다. 모델 다운로드와 RSS 수집에는 인터넷 연결이 필요합니다. 모델·Python 패키지를 위한 디스크 공간도 필요합니다.

### 4-2. Python 가상환경 만들기

**새 PC 또는 처음 설치하는 경우**에 실행합니다. 다른 PC의 `.venv`를 복사해서 사용하지 않습니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

가상환경은 프로젝트 전용 Python과 패키지를 보관하는 폴더입니다. 이 문서는 실행 파일을 직접 지정하므로 `Activate.ps1` 실행이나 PowerShell 실행 정책 변경이 필요하지 않습니다. 기존 환경을 사용하는 경우 새 가상환경 생성은 생략합니다.

### 4-3. Ollama 설치와 요약 모델 준비

1. [Ollama Windows 다운로드](https://ollama.com/download/windows)에서 설치 프로그램을 받아 설치합니다.
2. PowerShell을 새로 열고 확인합니다.

```powershell
ollama --version
ollama pull qwen3:4b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

`ollama list`와 API 결과에 `qwen3:4b`가 나타나면 모델을 사용할 준비가 된 것입니다. Ollama Windows 앱은 설치 후 백그라운드에서 동작합니다. 실행되지 않았다면 시작 메뉴에서 Ollama를 실행합니다. 앱 대신 직접 실행할 때는 **별도 터미널**에서 `ollama serve`를 실행하고 창을 유지합니다. [공식 Windows 안내](https://docs.ollama.com/windows), [Qwen3:4b 모델 안내](https://ollama.com/library/qwen3:4b)

`ollama serve`에서 `11434 ... bind ... already in use` 또는 `Only one usage ...`가 나오면 이미 Ollama가 실행 중일 수 있습니다. 먼저 위 API 조회로 확인하고 두 개를 동시에 실행하지 않습니다.

### 4-4. 임베딩 모델 준비

4-2의 의존성 설치에 Sentence Transformers가 포함됩니다. 메인에서 처음 검색하면 필요한 E5 모델을 자동으로 다운로드하고 CPU에 로드합니다.

서버 실행 전에 모델만 미리 준비하고 싶다면 프로젝트 루트에서 아래 명령을 실행할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe -c "from dait.pipelines.search_compare import load_encoder; load_encoder('intfloat/multilingual-e5-small'); print('임베딩 모델 준비 완료')"
```

이 명령은 모델을 다운로드·로드하며 기사 수집이나 요약 생성은 하지 않습니다. 기사 색인은 이후 통합 검색 시 생성·갱신됩니다. 모델 파일은 라이브러리의 로컬 캐시에 저장되며 Git에서 받는 파일이 아닙니다.

### 4-5. 기사 데이터 준비

`data/real_articles.db`가 함께 전달되었다면 기존 기사로 시작할 수 있습니다. 없거나 새 기사를 받고 싶다면 수집합니다.

```powershell
.\.venv\Scripts\python.exe -m dait.pipelines.collect_news
.\.venv\Scripts\python.exe -m dait.pipelines.check_news
```

현재 수집 출처는 전자신문·TechCrunch·The Verge의 설정된 공개 RSS입니다. URL 중복을 제거하고 최신 50개를 저장합니다. 50개 미만이거나 수집·저장에 실패하면 기존 데이터를 보존하는 정책입니다. 짧은 간격으로 수집하면 같은 기사만 들어올 수 있으며, 이때 기존 요약을 재사용하는 것이 정상입니다.

### 4-6. 웹 서버 실행

Ollama를 켠 상태에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn dait.main:app --host 127.0.0.1 --port 8000
```

터미널을 유지한 채 브라우저에서 [DAIT 메인](http://127.0.0.1:8000/)을 엽니다. HTML 파일을 더블클릭하는 방식이 아닙니다. API 문서는 [FastAPI 문서](http://127.0.0.1:8000/docs)에서 볼 수 있습니다.

서버 시작 시 미처리 기사 요약이 자동으로 시작합니다. 저장된 요약을 읽는 데는 Ollama가 필요 없지만, Ollama가 꺼져 있으면 새 요약 작업은 실패·재시도 상태가 됩니다.

## 5. 처음 이용할 때 확인할 흐름

1. 비로그인 메인에서 최신 기사와 저장된 요약을 확인합니다.
2. 로그인 팝업의 회원가입으로 계정을 만듭니다. 아이디는 공백 없이 최대 30자, 비밀번호는 5~128자이며 확인 값이 같아야 합니다. 현재는 이메일 인증 방식이 아닙니다.
3. 가입 후 별도로 로그인합니다. 관심사를 저장하지 않은 회원은 로그인 직후 선택 화면을 보지만, 로고·메뉴·다음에 하기로 다른 화면을 이용할 수 있습니다.
4. 관심 카테고리를 저장하면 해당 계정의 맞춤 목록에 반영됩니다.
5. 검색어를 입력하고 의미 검색이 끝나면 카드의 유사도를 확인합니다. 첫 실행은 모델과 색인 준비 때문에 더 오래 걸릴 수 있습니다.
6. 미처리 기사 상세 팝업을 열어두면 저장 상태가 약 3초마다 갱신됩니다. 요약 완료 시 메인과 같은 문장이 표시됩니다.

개발용 `user1`, `user2`, `user3`와 공통 비밀번호 `1234`도 호환 목적으로 코드에 남아 있습니다. 새로 가입하는 회원의 5자 이상 비밀번호 정책과 다릅니다. 현재 인증은 운영 배포용으로 완성된 상태가 아닙니다.

## 6. 다음 실행·추가 수집·종료

다음 실행부터는 설치를 반복하지 않고 **Ollama 실행 → FastAPI 실행 → 브라우저 접속** 순서로 사용합니다. 새 기사 수집은 서버와 별도 터미널에서 4-5의 수집 명령을 실행하면 됩니다. 주기적인 수집 예약은 아직 구현하지 않았습니다.

서버를 종료하려면 서버 터미널에서 `Ctrl+C`를 누릅니다.

```powershell
ollama ps
ollama stop qwen3:4b
```

`ollama stop`은 모델을 메모리에서 내리는 명령입니다. FastAPI 작업자가 계속 요청하면 다시 로드될 수 있습니다. 자동 요약을 멈추려면 먼저 FastAPI를 종료합니다. Ollama까지 완전히 끄려면 작업표시줄 숨겨진 아이콘에서 Ollama를 우클릭하여 Quit/종료를 선택합니다. 직접 `ollama serve`로 실행했다면 해당 터미널에서 `Ctrl+C`를 누릅니다. [Ollama Windows 동작 안내](https://docs.ollama.com/windows)

## 7. 기술 스택과 파일 위치

| 기술 | 사용 목적 |
|---|---|
| Python / FastAPI / Uvicorn | API와 웹 서버, 처리 작업 연결 |
| Pydantic v2 | 가입·로그인·검색·관심사 입력 검증 |
| SQLite | 기사·회원·세션·관심사·요약·색인·대기열 저장 |
| pwdlib / Argon2 | 가입 회원 비밀번호 해시·검증 |
| HTML / CSS / JavaScript | 서버 렌더링 화면과 검색·팝업·자동 갱신 |
| Ollama / Qwen3:4b | RSS 기반 요약·한국어 제목 생성 |
| Sentence Transformers / E5-small | CPU 임베딩과 의미 검색 |
| pytest / unittest.mock | 격리 단위 테스트·가짜 외부 서비스 |
| Ruff / Pyright | 코드 품질과 타입 검사 |

```text
DAIT_ui_v1.0.1/
├─ data/                            로컬 SQLite 데이터
├─ docs/                            구조·테스트 문서 및 HANDOFF.md
├─ scripts/                         검사 실행 도구
├─ src/
│  ├─ dait/             API·서비스·DB 접근·수집 코드
│  ├─ backend/          이전 backend.* 경로 호환 코드
│  └─ frontend/        화면 렌더러·assets(CSS/JavaScript)
├─ tests/                           단위 테스트 및 기존 회귀 검사
├─ .gitignore                       Git 제외 규칙
├─ pyproject.toml                   패키지·pytest·Ruff·Pyright 설정
├─ README.md                        설치 및 실행 안내
├─ requirements.txt                서비스 실행 의존성
└─ requirements-dev.lock.txt       테스트 의존성 고정 목록

```

위 폴더 구조를 기준으로 수정 위치를 확인합니다. 구조 안내와 과거 구조 대응표는 이동 이전 기록일 수 있습니다. `ui_step1~5`의 과거 실행 명령 대신 이 문서의 `python -m dait.pipelines...` 명령을 사용합니다.

## 8. 데이터·모델과 Git 업로드 정책

| 파일·폴더 | 정책 |
|---|---|
| 소스·테스트·현재 문서·의존성 고정 파일 | 업로드 대상 |
| `data/real_articles.db` | 공유 기사 데이터 유지 |
| `data/summary_tests.db`, `data/foreign_translations.db` | 저장된 생성 결과 재현용으로 유지 |
| `data/users.db` | 회원·세션 포함, Git 제외 |
| `data/summary_queue.db`, 잠금·SQLite 임시 파일 | 로컬 작업 상태, Git 제외 |
| `data/search_index.db` | 재생성 가능한 임베딩 색인, Git 제외 |
| 모델 가중치·모델 캐시·가상환경 | PC별 설치, Git 제외 |
| `.tmp/`, `data/reports/`, 검사 캐시·로그 | 자동 생성물, Git 제외 |
| `archive/` | 과거 코드·DB 보관본, Git 제외 |

다른 PC에서는 모델과 가상환경을 다시 준비합니다. 색인이 없어도 검색 시 준비하지만, 기사 DB가 없다면 수집이 먼저 필요합니다. 회원 DB가 Git에 없으므로 기존 PC의 회원 계정이 자동 전달되지는 않습니다. 실제 데이터를 초기화하려고 DB를 임의로 삭제하지 않습니다.

## 9. 자동 단위 테스트와 최근 결과

### 실행 방법

서비스 `.venv`와 분리된 테스트 환경을 만듭니다. 테스트 환경에는 실제 모델을 설치하거나 실행할 필요가 없습니다.

```powershell
py -m venv .venv-test
.\.venv-test\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv-test\Scripts\python.exe -m pip install -e . --no-deps
.\.venv-test\Scripts\python.exe scripts\run_unit_tests.py
```

스크립트는 pytest, Ruff 검사·포맷 확인, Pyright를 실행하고 `.tmp/test-results/`에 결과를 저장합니다. Pyright에는 Node.js 실행 환경이 필요합니다. 각 단위 검사는 임시 DB와 mock/fake를 사용하며, 실제 회원·기사 DB와 외부 서비스 접근을 차단합니다.

### 2026-11-09 실행 결과

아래는 백엔드 패키지 전환 이전 Python 3.12.14 전용 테스트 환경의 기록입니다. 이후 파일 정리 후 화면 단위 테스트 15개 통과를 확인했으며 전체 회귀 결과는 아닙니다. 사용 PC의 서비스 Python 3.13.14 환경을 교체한 것은 아닙니다.

| 항목 | 결과 |
|---|---:|
| 자동 검사 | 118개 |
| 통과 / 실패 | 106 / 12 |
| 환경 오류 / skip / xfail | 0 / 0 / 0 |
| 정순·역순 비교 | 118개 결과 동일 |
| Python 라인 / 분기 커버리지 | 52.7% / 36.8% |
| Ruff 진단 / 포맷 필요 | 45건 / 30개 파일 |
| Pyright strict 오류 | 1,616건 |

**문서 기준 전체 완료·품질 게이트 통과 상태가 아닙니다.** 실패 12개는 문서 ID 9개에 해당하며 다음 차이를 포함합니다.

- 가입 직후 자동 로그인·이메일 형식 검증 기대와 현재 가입/로그인 방식의 차이
- 검색어 100자 제한·요약문 검색 기대와 현재 200자·제목/RSS 검색의 차이
- HTTP 링크 차단, READY 기사만 공개, 상세 오류 코드에 관한 차이
- 요약의 수치 변형 자동 검증과 사설 IP 수집 요청 사전 차단의 부재

문서 139개 UT ID 중 실패 9개, 일부 기대결과만 검사한 항목 36개, 미구현 27개, 설계 차이 26개, 미검증 41개입니다. 118개 실행 케이스 수와 문서 ID 수는 다릅니다. 커버리지에는 브라우저 JavaScript·CSS 동작이 포함되지 않습니다. 타입 오류 수 전체를 런타임 결함 수로 해석하지 않습니다.

- [검사 준비·격리·판정 방법](docs/testing/UNIT_TEST_GUIDE.md)
- [최근 결과와 실패 원인](docs/testing/UNIT_TEST_RESULTS.md)
- [현재 PC의 자동 생성 상세 보고서](.tmp/test-results/REPORT.md) — Git 제외 파일이므로 다른 PC에는 없을 수 있음

사용자가 브라우저에서 확인한 검색·자동 요약·메인/상세 일치·실패 복구·팝업 갱신 결과와, 문서의 엄격한 단위 테스트 판정은 구분합니다. 새 PC의 설치·실제 모델 생성 품질은 그 PC에서 별도로 확인해야 합니다.

## 10. 자주 겪는 문제

| 증상 | 확인 방법 |
|---|---|
| Python 명령을 못 찾음 | 설치 후 터미널을 다시 열고 `py --version` 또는 `python --version` 확인 |
| 복사한 `.venv`가 실행되지 않음 | PC별 경로가 달라질 수 있으므로 새 가상환경 생성 후 의존성 설치 |
| `No module named backend` | `DAIT_ui` 루트에서 실행하는지 확인 |
| `WinError 10061` / Ollama 연결 거부 | Ollama 실행 후 `Invoke-RestMethod http://127.0.0.1:11434/api/tags` 확인 |
| Ollama 포트 11434 중복 오류 | 이미 실행 중인지 API 조회. 두 번째 `ollama serve`는 불필요 |
| 요약 버튼을 눌러도 대기 | 현재 생성 중인 기사가 끝난 뒤 순차 처리. 상태와 앞선 작업 수 확인 |
| 정보 부족 | RSS 정보가 세 요점을 만들기에 부족한 상태. 성공 요약으로 바꾸지 않음 |
| 검색 유사도가 아직 없음 | 의미 검색 준비/오류 안내 확인. 최초 모델·색인 준비는 시간이 걸릴 수 있음 |
| 모델 가중치 파일 누락 오류 | 다운로드가 완료됐는지 4-4의 준비 명령으로 확인. 캐시를 무작정 삭제하지 말고 오류 경로를 점검 |
| 수집해도 새 기사가 없음 | RSS 업데이트 전에는 같은 기사가 재수집될 수 있음 |
| 화면 수정이 반영되지 않음 | 서버 재시작 후 브라우저 `Ctrl+F5` |
| 자동 검사 종료 코드 1 | 현재 문서 차이·품질 게이트 실패가 남아 있음. 보고서에서 실제 실패 항목 확인 |

## 11. 현재 범위 밖의 기능

예약 수집, 알림 발송, 관련 뉴스, Redis 캐시, 운영용 PostgreSQL·Docker 구성, refresh 토큰 회전, 회원탈퇴 등은 현재 완료 기능으로 안내하지 않습니다. 외부 무료 AI API 연결도 보류 상태입니다.

**이메일 인증과 회원 인증 완성 작업(기존에 정한 5단계)은 사용자가 `5단계 작업 진행하자`라고 명시적으로 요청할 때만 진행합니다.**

현재 작업 기록은 [HANDOFF.md](docs/HANDOFF.md)를 확인하세요.

## 다른 위치로 복사하기

서버를 종료한 뒤 필요한 회원 DB `data/users.db`를 포함해 복사합니다. 회원 DB는 사본마다 다를 수 있으므로 사용할 DB를 확인하세요. `.venv`, `__pycache__`, `*.egg-info`, 테스트 임시 폴더는 제외하고 새 위치에서 가상환경을 다시 만듭니다. 뉴스를 새로 수집하려면 기존 뉴스·요약·번역·검색 DB를 복사하지 않고 4-5의 수집 명령을 실행합니다. 원본 데이터는 삭제하지 않습니다.
