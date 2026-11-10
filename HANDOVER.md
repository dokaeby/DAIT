# Project_DAIT 개발 인수인계서 (Handover Document)

- **최종 업데이트일**: 2026-11-08
- **프로젝트명**: 다잇 (Project_DAIT)
- **담당 파트**: 17개 국내외 언론사 실수집, Trafilatura 본문 추출, 구글 번역(Google Translate) 기반 AI 3줄 요약·번역, 인기도/키워드 점수화 랭킹 파이프라인 및 FastAPI + 화이트 테마 웹 큐레이션 구축
- **목적**: 개발 환경 간 무중단 작업 전환, 아키텍처 및 최근 고도화 이력 공유, 프론트엔드/백엔드/배포(Render) 연동 가이드 제공

---

## 1. 프로젝트 핵심 개발 원칙 (절대 위반 금지)
1. **기술 스택**: Python 3.14+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Redis, SQLite(로컬/테스트)/PostgreSQL(운영), Trafilatura, deep-translator(`GoogleTranslator`), uv/pip
2. **타입 원칙**:
   - 모든 시스템 경계는 `Pydantic v2 ConfigDict(extra="forbid", frozen=True)` 통과
   - 함수/모델 전반에 `Any`, `dict` 사용 엄격 금지 (`pyright strict` 통과)
3. **보안/운영 원칙**:
   - `print()` 금지 (`logging` 구조화 모듈 사용)
   - 수집 및 본문 추출 시 SSRF 차단 (사설망 `127.0.0.1`, `10/8`, `192.168/16`, 링크로컬/클라우드 메타데이터 `169.254.169.254` 등 원천 차단)
   - `robots.txt` 준수, 응답 크기 제한, HTTPS 필수
4. **파이프라인 및 요약 품질 원칙**:
   - 가짜 시드/더미 데이터 및 메타성 안내 문구(`"OO에서 보도한..."`, `"원문 보기 링크를 통해..."` 등) 생성·노출 절대 금지
   - `canonical_url UNIQUE`로 중복 기사 수집 차단 및 언론사 메인 도메인(`/`)이 아닌 **개별 기사 상세 본문 URL(`<item><link>`)** 바인딩 강제
   - 오픈소스 텍스트 마이닝 도구 **Trafilatura**(`trafilatura.extract(..., include_comments=False, include_tables=False)`)로 HTML 광고·네비게이션·바이라인을 제거하고 **오로지 기사 본문 팩트**에 기반한 **정확히 3줄 요약(`summary_lines`)** 생성
   - 해외 외신 기사(`TechCrunch`, `MIT Tech Review`, `The Verge`)는 **원문 제목을 그대로 보존**하고 하단에 **`번역 : {번역된 기사제목}`**(제목 글씨 크기의 70%)을 병기하며, 3줄 요약문은 `deep-translator`(`GoogleTranslator`)를 통해 한국어로 자동 번역

---

## 2. 현재 작업 완료 상태 (Task 1 ~ Task 10 전 구간 완료)

모든 단위/통합/API 계약 테스트, 정적 분석(Ruff/Pyright Strict), 실제 17개 언론사 RSS 수집·요약·번역 및 프론트엔드 UI 개편까지 100% 완료한 상태입니다.

| 구분 | 모듈 계층 | 구현 파일 | 구현 내용 및 검증 상태 | 상태 |
|---|---|---|---|---|
| **Task 1~2** | **Schemas & Taxonomy** | `src/backend/app/schemas/collector.py`<br>`src/backend/app/schemas/content.py`<br>`src/backend/app/schemas/news.py`<br>`src/backend/app/core/taxonomy.py` | • Pydantic v2 불변 모델 (`extra="forbid"`, `frozen=True`)<br>• 3대 카테고리(`AI`, `ECONOMY`, `SOCIETY`) 및 15개 하위 키워드 분류 체계<br>• 국내 14곳 + 해외 3곳(총 17곳) 공식 언론사 RSS 피드 레지스트리 | 완료 (100%) |
| **Task 3** | **Collectors & Extractor** | `src/backend/app/collectors/rss_collector.py`<br>`src/backend/app/collectors/content_extractor.py` | • SSRF/사설 IP 차단 방어 및 `<item><link>` 개별 기사 상세 URL 추출<br>• `Trafilatura` 연동으로 광고·푸터·바이라인 배제 및 순수 본문 문단 고정밀 추출 | 완료 (100%) |
| **Task 4** | **AI & Translation Workers** | `src/backend/app/workers/ai_processor.py`<br>`src/backend/app/workers/collector_worker.py` | • 프롬프트 인젝션/PII 방어 및 `content_hash` 기반 캐시<br>• `deep-translator`(`GoogleTranslator`) 연동 해외 기사 제목·본문 3줄 요약 한국어 번역<br>• 해외 기사 제목 `{원문 제목} \|\|\| {번역된 제목}` 병기 및 특수기호(`\|`, 불균형 따옴표) 정제 | 완료 (100%) |
| **Task 5** | **Repositories** | `src/backend/app/repositories/news_repository.py` | • SQLite/PostgreSQL 비동기 DB 기반 `canonical_url UNIQUE` 중복 차단<br>• `news` + `content_results` 1:1 원자적 트랜잭션 저장 | 완료 (100%) |
| **Task 6** | **Services & Ranking** | `src/backend/app/services/ranking_service.py`<br>`src/backend/app/services/news_service.py` | • 최신성 + 출처 우선순위 + 키워드 출현 빈도 + 인기도 가중치 합산 결정적 랭킹 산출<br>• 레거시 메타/더미 문구 실시간 필터링 및 Redis 캐시/DB Fallback | 완료 (100%) |
| **Task 7~10** | **API (v1) & Web UI** | `src/backend/app/api/main.py`<br>`src/backend/app/api/v1/news.py`<br>`src/frontend/public/index.html`<br>`src/frontend/public/detail.html`<br>`src/frontend/public/mockup.css` | • 화이트 라이트 테마(`#f8fafc` / `#ffffff`) 전면 적용<br>• `전체 보기` / `국내 뉴스 (14곳)` / `해외 뉴스 (3곳)` 권역 탭 분리<br>• 해외 기사 원문 제목 노출 + 하단 `번역 : 번역된 기사제목` (70% 글씨 크기) 렌더링<br>• 3줄 요약 기본 숨김(`display: none`) 및 `[요약문 보기]` / `[요약문 닫기]` 단일 토글 UI | **완료 (100%)** |

### 2.1 자동화 품질 게이트 (Quality Gate)
- `ruff check .` : **PASS** (`All checks passed!`)
- `ruff format --check .` : **PASS** (`29 files already formatted`)
- `pyright --pythonpath .\.venv\Scripts\python.exe` : **Strict 0 errors, 0 warnings, 0 informations PASS**
- `pytest -q` : **총 288개 테스트 전원 통과 (`288 passed`) — 최신 검증: 10절**

---

## 3. 최근 주요 수정 및 고도화 이력 (상세)

### 3.1 개별 기사 상세 URL(`canonical_url` / `original_url`) 정상화 및 더미 데이터 영구 제거
- **개별 기사 링크 추출 (`src/backend/app/collectors/rss_collector.py`)**:
  - RSS `<channel><link>`(언론사 홈페이지 루트)를 절대 참조하지 않고, 각 `<item>`(또는 Atom `<entry>`) 내부의 `<link>` 및 `<guid isPermaLink="true">`에서 개별 기사 고유 상세 URL을 추출합니다.
  - 루트 경로(`/`)만 있는 도메인 메인 URL은 수집 단계에서 즉시 거부(`rejected_count` 처리)합니다.
- **메타성 안내 문구 및 가짜 시드 전면 삭제 (`src/backend/app/api/main.py`, `src/backend/app/services/news_service.py`, `src/backend/app/workers/ai_processor.py`)**:
  - `"서울경제에서 보도한..."`, `"원문 보기 링크를 통해..."`, `"전체 본문을 확인할 수 있습니다"` 등의 메타 안내 문구를 생성하던 폴백 로직을 완전히 제거했습니다.
  - 기존 DB(`dait.db`)에 해당 패턴(`_LEGACY_DUMMY_PATTERNS`)이 남아 있는 경우 서버 기동 시 자동으로 감지하여 초기화 및 재수집하며, 조회 계층(`NewsService`)에서도 이중으로 필터링합니다.

### 3.2 오픈소스 텍스트 마이닝(Trafilatura) 기반 순수 본문 3줄 요약 파이프라인 구축
- **고정밀 본문 추출기 (`src/backend/app/collectors/content_extractor.py`)**:
  - `extract_clean_body_with_trafilatura(raw_html)`: `trafilatura.extract(..., include_comments=False, include_tables=False, favor_precision=True)`를 사용해 HTML 내 광고, 헤더, 푸터, 저작권 문구를 제거하고 본문 팩트 문단만 추출합니다.
  - `fetch_article_body_with_trafilatura(url)`: RSS 요약문이 짧은 경우 SSRF 검증(사설/루프백 IP 차단)을 거친 뒤 원문 웹페이지에서 본문을 추출합니다.
- **순수 본문 팩트 기반 3줄 요약 (`_build_three_factual_sentences`)**:
  - 기자 바이라인(`_BYLINE_PATTERN`)과 저작권 상투구(`_BOILERPLATE_PATTERN`)를 제거한 뒤, 오로지 기사 본문 문장과 절(Clause)만 추출하여 마침표(`.`)로 끝나는 완결된 한국어 3문장을 구성합니다.
  - `ensure_terminal_punctuation`에서 번역 시 발생할 수 있는 파이프 기호(`|`)와 짝이 맞지 않는 따옴표(`"`, `“`, `”`)를 자동 제거합니다.

### 3.3 구글 번역(`deep-translator`) 연동 및 해외 기사 제목·요약 표시 방식 개편
- **해외 기사 원문 제목 유지 + 하단 번역 제목 병기 (`TranslatingNewsCollector`)**:
  - 해외 외신(`TechCrunch`, `MIT Tech Review`, `The Verge`) 수집 시 기존 `NewsListItem`의 10개 필드 계약을 깨지 않으면서 원문과 번역문을 모두 전달하기 위해 제목을 **`{원문 기사 제목} ||| {한국어 번역 제목}`** 형식으로 저장합니다.
  - 덕분에 키워드 검색(`q=...`) 시 영어 원문 키워드와 한국어 번역 키워드 모두로 검색이 가능합니다.
- **프론트엔드 카드 렌더링 (`src/frontend/public/index.html`, `src/frontend/public/detail.html`, `src/frontend/public/mockup.css`)**:
  - 카드 상단 메인 제목(`h2.card-title`, `1.3rem`)에는 **해외 기사의 영어 원문 제목 그대로** 표시합니다.
  - 메인 제목 바로 아래에 `<p class="card-translated-title">번역 : {번역된 기사제목}</p>`을 렌더링하며, 글씨 크기는 메인 제목의 **70% (`font-size: calc(1.3rem * 0.7);` = `0.91rem`)**로 적용했습니다.
  - 국내/해외 기사 모두 3줄 요약문(`ul.summary-list`)은 기본 숨김(`display: none`) 상태이며, 하단 **`[요약문 보기]` / `[요약문 닫기]`** 단일 토글 버튼을 클릭하면 한국어 3줄 요약문이 펼쳐집니다.

---

## 4. 프론트엔드 및 API 엔드포인트 호출 규격 요약

서버 실행 명령어:
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.backend.app.api.main:app --reload
```

### 4.1 뉴스 목록 조회: `GET /v1/news`
- **호출 예시**: `GET /v1/news?category=AI&q=AI 에이전트&sort=rank&page_size=20`
- **Query Parameters (`NewsQuery`)**:
  | 파라미터 | 타입 | 기본값 | 필수 여부 | 제약 조건 및 설명 |
  |---|---|---|---|---|
  | `category` | `"AI" \| "ECONOMY" \| "SOCIETY"` | `"AI"` | 선택 | 3대 카테고리 (`AI`, `ECONOMY`, `SOCIETY`) |
  | `q` | `string \| null` | `null` | 선택 | 하위 키워드 또는 검색어 (최대 200자, 제목·본문·키워드 매칭) |
  | `sort` | `"rank" \| "latest"` | `"rank"` | 선택 | 정렬 기준 (`"rank"`: 인기도·키워드·최신·출처우선순위순, `"latest"`: 최신순) |
  | `page_size` | `integer` | `10` | 선택 | 페이지당 항목 수 (`1` ~ `50`) |
  | `cursor` | `string \| null` | `null` | 선택 | 커서 기반 페이지네이션 토큰 (`1` ~ `2048`자) |

### 4.2 뉴스 상세 조회: `GET /v1/news/{news_id}`
- **호출 예시**: `GET /v1/news/{news_id}`
- **응답**: `NewsDetailResponse` (`article`, `content`, `source`, `related_news`, `processing`)

### 4.3 웹 화면 라우트
- `GET /` : 화이트 라이트 테마 기반 메인 뉴스 큐레이션 화면 (`src/frontend/public/index.html`)
- `GET /detail.html?id={news_id}` : 뉴스 상세 및 3줄 요약 화면 (`src/frontend/public/detail.html`)
- `GET /healthz` : 헬스 체크 (`{"status": "ok"}`)

---

## 5. 배포(Render) 및 Git 브랜치 동기화 가이드

현재 로컬 개발 브랜치는 `feat/pipeline-core`이며, Render 운영 서버(`project-dait.onrender.com`)는 `origin/main` 브랜치를 바라보고 배포됩니다. 따라서 수정 사항을 배포할 때는 아래 명령어로 `feat/pipeline-core`와 `main` 브랜치를 함께 푸시해야 합니다.

```powershell
git add requirements.txt pyproject.toml dait.db HANDOVER.md typings/ src/ tests/
git commit -m "docs: update HANDOVER.md with Trafilatura, Google Translate, and dual-title UI changes"
git branch -f main HEAD
git push origin feat/pipeline-core
git push origin HEAD:main
```


---

## 6. 최근 수정: midterms 제목 번역 문맥 보정

- 사용자 요청: Gemini가 제안한 본문 Context 결합 방식의 타당성 검토 후 제목 번역 부분만 수정.
- 검토 결과: 제목만 번역하면 다의어 오역 가능성이 있다는 설명은 타당하나 제안 코드는 그대로 적용하지 않음. `translate_to_korean`과 하위 번역 함수가 입력/출력의 모든 공백을 합치므로 줄바꿈 뒤 Context를 붙이고 첫 줄만 추출해도 제목과 본문이 분리되지 않음. 원문 본문을 외부 제목 번역기로 추가 전송하는 문제도 있음.
- 변경 파일: `src/backend/app/workers/ai_processor.py`의 `TranslatingNewsCollector.collect` 내부 제목 번역 블록만 변경.
- 처리 방식: 원문 제목과 정제한 본문 첫 35단어를 로컬에서 검사. 제목에 `midterm(s)`가 있고 선거/의회/상원/정당/유권자 등 정치 문맥 단서가 있을 때 번역 입력의 해당 단어를 `midterm elections`로 명확화. 외부에는 제목만 전달하고 본문/Context는 전달하지 않음. 이미 `midterm elections`인 문구는 중복 확장하지 않음.
- 기존 원문 제목 및 `원문 ||| 번역` 형식은 유지. 번역 비활성화/실패 시 영어 보정문을 번역 제목으로 병기하지 않음. 정치 단서가 없으면 원래 번역 입력 유지. 이는 제한된 다의어 보정이며 모든 기사/번역기의 의미 정확성을 보장하는 NLP 판별기는 아님.
- 범위 확인: Git HEAD와 바이트 비교하여 제목 번역 블록 전후 코드가 동일함을 확인. `PrivacyGuard`, Redis 분산 캐시, `AIProcessor`, 3줄 요약 및 본문 번역 함수는 수정하지 않음.
- 신규 회귀 테스트: `tests/unit/test_title_translation_context.py`, 9개 사례. 정치/학업 문맥, 본문 없음, 명확한 선거 제목, 일반 제목, 본문 개인정보 비전송, 오프라인/번역 실패를 Fake 번역기로 검증. 신규 회귀 테스트는 외부 번역 호출 없음.
- 품질 게이트: `ruff check .` 통과, `ruff format --check .` 통과(27 files), `pyright --pythonpath .\.venv\Scripts\python.exe` 오류 0개. 기존 `reportAny` 설정 미지원 안내는 유지.
- 관련 회귀 검증: `python -m pytest tests/unit/test_title_translation_context.py tests/unit/test_ai_processor.py -q` → **72 passed**.
- 전체 검증: `python -m pytest -q --tb=short` → **266 passed, 1 failed**(총 267개). 실패는 `tests/unit/test_taxonomy_and_categories.py::test_application_crawls_rss_serves_categories_and_toggle_ui`의 `[요약문 보기]` 문구 기대와 현재 HTML 문구 불일치. `src/frontend/public/index.html`이 HEAD와 동일하고 HEAD HTML에도 해당 괄호 문구가 없음을 확인했으므로 이번 제목 번역 변경과 독립적인 기존 UI 계약 불일치임. 요청 범위를 지키기 위해 UI/기존 테스트는 수정하지 않음.
- 운영 주의: 이미 DB에 저장된 제목은 이 코드 변경만으로 갱신되지 않음. 운영 기사 재번역/갱신은 별도 승인된 절차로 수행해야 하며 DB 삭제나 자동 초기화는 이번 작업에서 실행하지 않음. 커밋/푸시/Render 배포도 실행하지 않음.
- 다음 작업 원칙: 후속 AI/엔지니어는 이 문서를 먼저 읽고, 작업 후 변경 범위·실행한 검증·남은 실패·운영 영향·다음 조치를 계속 추가 기록할 것. 기존 사용자 작성 내용을 임의로 덮어쓰지 말 것.


## 7. 후속 수정: 본문 전체·저장된 요약 기반 제목 보정

- 사용자 재현: Render 화면에서 영어 `midterms` 제목 번역은 `중간고사`인데 본문 요약은 `중간선거`인 불일치.
- 이전 보정은 첫 35단어의 영어 정치 단서에만 의존했고, 이미 저장된 DB/Redis 제목을 보정하지 않았음.
- `src/backend/app/core/title_translation.py`: 영어/한국어 정치 단서를 전체 전달 문맥에서 로컬 판별. 알려진 다의어 `midterms`의 번역 입력을 `midterm elections`로 명확화하고, 근거가 있는 기존 병기 제목의 `중간고사`/`중간 고사`를 `중간선거`로 교정. 학업 문맥에 정치 근거가 없으면 그대로 유지. 범용 의미 번역 엔진으로 오해하지 말 것.
- `src/backend/app/workers/ai_processor.py`: 첫 35단어 제한 제거, 정제한 본문 전체를 로컬 판정에 사용. 번역기로 보내는 데이터는 여전히 제목뿐이며 원문 제목 유지 및 실패/비활성화 처리는 유지.
- `src/backend/app/services/news_service.py`: DB 기반 홈 목록/API 목록/관련 뉴스에 본문+번역문+요약을 근거로 제목 보정. Redis 홈 목록·상세 캐시 적중 시에는 캐시의 번역문·요약 근거로 교정. DB 원본이나 요약을 다시 쓰거나 초기화하지 않음. URL/ID/3줄 요약/기존 Redis 캐시 키·TTL은 유지.
- 변경 금지 범위 확인: `AIProcessor`, `RedisContentCache`, `GoogleTranslateContentProcessor`, `_safe_text`, `_validate_preservation`, `translate_to_korean` 구현은 HEAD와 소스 비교로 동일함을 확인.
- 신규/확장 테스트: `tests/unit/test_title_translation.py`, `test_title_translation_context.py`, `test_news_service.py`. 본문 35단어 이후 문맥, 한국어 요약, 기존 DB 제목, 기존 Redis 목록·상세 캐시, 학업 기사 보존을 검증.
- 검증: Ruff/포맷 통과(29 files), strict Pyright 오류 0개(기존 reportAny 미지원 안내 유지). 관련 회귀 테스트 **115 passed**. 전체 **276 passed, 1 failed**(277개); 남은 실패는 앞서 기록한 변경 범위 밖 UI 문구 `[요약문 보기]` 검사 불일치.
- 외부 전송 승인 제한: 정제한 본문 일부를 Google 번역에 추가 전송하는 구분자 기반 문맥 번역 변경은 자동 승인 검토에서 거절되어 실행되지 않았음. 거절 사유는 추가 본문 payload와 외부 대상에 대한 명시적 사용자 승인이 없다는 것. 우회하지 않았고 이번 구현에는 새 본문 외부 전송이 없음. 해당 방식은 사용자 승인을 받은 뒤 별도 검토해야 함.
- 배포: 커밋/푸시/Render 배포 미실행. 확인 당시 로컬 `feat/pipeline-core`와 `main`은 다른 커밋을 가리켰고 main에는 전차 제목 보정 커밋이 포함되지 않았음. 원격 서비스의 실제 배포 버전은 검증하지 못했으므로 변경을 운영에 배포하기 전후 버전을 확인할 것. 운영 화면은 로컬 수정만으로 바뀌지 않음.


## 8. 사용자 승인 후: Google 본문 문맥을 반영하는 제목 번역

- 사용자 명시 승인: “정제된 본문 일부를 Google 번역에 함께 전송하는 방식을 승인합니다.” 이 승인으로 7절의 외부 전송 제한은 해당 제목 번역 범위에서 해소됨.
- `src/backend/app/workers/ai_processor.py`에 `translate_title_to_korean`과 제목 전용 `translate_title_context_to_korean` 추가. HTML 태그/바이라인 등을 제거하고 기존 `_safe_text`의 개인정보 패턴 정제·인젝션 검사를 통과한 본문 일부(최대 500자)를 Google 번역에 제목과 함께 전송. 전체 요청은 기존 한도에 맞춰 900자 이내로 제한.
- 문맥과 제목은 고정 구분자 `⟪713149⟫`, `⟪862953⟫`로 분리. 줄바꿈이 공백으로 합쳐져도 두 구분자 사이의 번역 제목만 추출. 구분자 손실·중복·역순·미번역·길이 초과는 제목 단독 번역으로 재시도하고, 본문 문맥이 제목에 섞인 응답을 그대로 저장하지 않음. 비활성화 시 문맥 외부 전송 없음.
- 실제 점검에서 기존 GTX 폴백의 첫 조각만 읽는 파싱이 문맥 뒤의 제목을 잃는 문제를 확인. 기존 본문 번역 함수는 변경하지 않고, 제목 전용 경로에서 Pydantic TypeAdapter로 Google의 가변 길이 응답과 모든 번역 조각의 문자열을 검증·결합하도록 수정.
- 제목 전용 GTX는 고정 Google URL과 저수준 httpx 전송을 사용하여 문맥이 담긴 URL이 httpx INFO 요청 로그에 남는 것을 피함. 새 어댑터 진단은 고정 문구만 사용하고 본문·번역 요청·예외 상세를 로그에 넣지 않음.
- `AIProcessor`, `RedisContentCache`, `GoogleTranslateContentProcessor`, `_safe_text`, `_validate_preservation`, `translate_to_korean`, 기존 `_translate_with_google_gtx` 구현은 HEAD와 소스 비교로 동일함을 확인. 7절의 기존 DB·캐시 표시 제목 보정도 유지.
- 테스트: `tests/unit/test_title_translation_context.py` 22개 사례. 같은 제목+다른 본문 문맥, 개인정보 패턴 정제, HTML 제거, 입력 크기 제한, 인젝션 문맥 배제, 구분자 실패 폴백, 오프라인, 공백 평탄화, 다중 GTX 응답 조각을 Mock으로 검증.
- 실제 Google 검증: 개인정보 없는 합성 선거 문장으로 문맥 전송과 두 구분자 보존, 제목만 추출됨을 확인. 반환 예: `중간 선거 후 데이터 센터는 새로운 규칙에 직면합니다`. primary deep-translator는 TooManyRequests를 반환했으나 제목 전용 GTX 폴백은 성공했으며, 최종 저수준 전송 경로도 실제 확인함. 신규 단위 테스트 자체는 Mock 기반이며 별도 실제 검증에서만 Google 연결을 사용.
- 품질 게이트: Ruff 검사/포맷 통과(29 files), Pyright strict 오류 0개. 기존 reportAny 미지원 안내 유지. 관련 회귀 **126 passed**. 전체 **287 passed, 1 failed**(288개); 실패는 기존 `test_application_crawls_rss_serves_categories_and_toggle_ui`의 `[요약문 보기]` 문구 기대 불일치로 이번 범위에서 수정하지 않음.
- 배포 상태: 커밋/푸시/Render 배포 미실행. 운영 사이트 반영에는 승인된 배포 절차가 별도로 필요. 기존 DB를 삭제하거나 재수집/일괄 재번역하지 않음.


## 9. origin/main 반영 및 Render 운영 화면 검증 완료

- 사용자 승인 범위: 수정 커밋 → origin/main 반영 → Render 배포 → 실제 화면 검증 → HANDOVER 결과 기록.
- 배포 코드 커밋: `2837555e5386201db500957f81c58990e7672524` (`fix: translate news titles with sanitized article context`). `origin/main`에 `d1a2a7c..2837555`를 강제 푸시 없이 fast-forward 반영했으며 `git ls-remote origin refs/heads/main`으로 SHA를 확인.
- 전체 배포 트리 확인: `src/backend/app/core/title_translation.py`, `src/backend/app/services/news_service.py`, 관련 테스트는 앞선 `750efba` 커밋에 이미 포함되어 있음. 최초 자동 승인 검토가 누락을 우려해 커밋/푸시를 거절했으나, `git ls-tree`, HEAD 소스, origin/main 대비 전체 diff와 조상 관계를 확인한 뒤 모든 필요한 경로를 명시하여 정상 승인·푸시 완료. 파일 누락이나 강제 푸시는 없음.
- 배포 전 검사: Ruff 검사·포맷 통과, strict Pyright 오류 0개, 관련 테스트 `126 passed`. 전체 테스트의 기존 UI 문구 검사 실패 1건은 8절에 기록된 상태로 유지.
- 운영 반영 확인: 최초 운영 API에는 기존 `중간고사 이후...`가 남아 있었으나 이후 root HTML의 SHA-256이 로컬 `src/frontend/public/index.html`과 일치하고 운영 API 제목이 `중간선거 이후...`로 전환된 것을 관찰.
- 실제 브라우저 검증: **2026-11-08 21:25:57 KST**. 기본 CUA 도구는 샌드박스 런타임 오류로 초기화 실패하여 독립 headless Chrome/Playwright로 공개 운영 페이지를 확인. 사용자 브라우저 프로필·쿠키·인증정보는 사용하지 않음. Playwright는 로컬 검증 도구로만 설치했고 앱 requirements/pyproject에는 추가하지 않음.
- 확인 기사: `After the midterms, things are looking rocky for Elon Musk and data centers` (TechCrunch, id `a27fdfa7-d1d9-460d-ae09-62ab5f0dcbec`). 목록의 해외 뉴스 탭에서 번역 제목이 **`중간선거 이후 Elon Musk와 데이터 센터의 상황은 험난해 보입니다.`**로 표시되고, 요약문 보기 버튼을 눌러 3문장이 표시됨을 확인. 요약의 중간선거·유권자·정치인 문맥과 제목이 일치하고 `중간고사`는 제목에 없음.
- 상세 화면에서도 같은 번역 제목과 3줄 요약 표시를 확인. root `/`, 목록 API `/v1/news?category=AI&q=midterms&page_size=10`, 상세 HTML `/detail.html?id=...`, `/healthz` 모두 **HTTP 200**, 브라우저 pageerror **0건**.
- 증거 파일:
  - [운영 뉴스 카드](artifacts/verification/render-title-context-2837555.png)
  - [운영 상세 화면](artifacts/verification/render-title-context-detail-2837555.png)
  - [검증 시각·HTTP·제목·요약·오류 기록](artifacts/verification/render-title-context-2837555.json)
- 검증 범위: 운영 화면은 기존 DB 기사의 조회 시 문맥 보정이 적용됨을 확인한 것. Google 제목 문맥 번역 자체의 실제 외부 연동은 8절 합성 문장 검증에서 확인했으며, 운영 DB를 삭제하거나 신규 재수집/일괄 재번역을 강제하지 않음.
- 상태 근거의 한계: Render API 키가 없고 비인증 GitHub 상태 API는 404였으므로 Render 컨트롤 플레인의 deploy id/로그는 확인하지 못함. 대신 원격 main SHA, 운영 HTML 일치, 실제 운영 API·목록/상세 브라우저 동작으로 공개 서비스 반영과 정상 응답을 확인.
- 이 결과·증거는 별도 문서 커밋으로 origin/main에 추가 반영. 코드 변경이 없는 기록용 커밋에는 `[skip render]`를 사용하여 확인된 배포를 불필요하게 다시 시작하지 않음(Render 공식 문서: https://render.com/docs/deploys#skipping-an-auto-deploy).


## 10. 현재 홈 화면 계약에 맞춘 UI 테스트 갱신 — 전체 288개 통과

- 사용자 요청: 남은 `[요약문 보기]` UI 문구 테스트를 현재 화면에 맞게 수정하고, 전체 통과 후 HANDOVER 기록 및 origin/main 반영.
- 변경 파일: `tests/unit/test_taxonomy_and_categories.py`의 `test_application_crawls_rss_serves_categories_and_toggle_ui`와 이 문서만 변경. 애플리케이션·HTML·CSS·번역·DB·캐시 구현은 수정하지 않음.
- 원인: 홈 화면은 대괄호 없는 `요약문 보기`/`요약문 닫기`, `.btn-toggle`, `.summary-box`, 원문 `.card-title-main`/번역 `.card-title-sub` 구조를 사용하지만 테스트는 이전 괄호 문구·`.card-translated-title`·`번역 : ${translatedTitle}` 템플릿을 기대했음.
- 수정: 현재 버튼 문구·토글 연결·요약 영역·원문/번역 제목 요소에 맞춰 검증 기대값 갱신. 상세 화면에서 사용하는 기존 괄호 문구나 실제 UI는 변경하지 않음. 기존 언론사 필터·카테고리/API·상세 조회·스타일 검증은 유지.
- 최종 품질 게이트:
  - `ruff check .`: PASS (`All checks passed!`).
  - `ruff format --check .`: PASS (`29 files already formatted`).
  - `pyright --pythonpath .\.venv\Scripts\python.exe`: PASS (`0 errors, 0 warnings, 0 informations`). 기존 `reportAny` 설정 미지원 안내는 별도로 남아 있음.
  - `python -m pytest -q --tb=short`: **288 passed in 6.52s**. 실패 0개. 7~9절에 기록된 UI 테스트 실패는 이 변경으로 해소됨.
  - 보안/로그: 제품 코드는 변경하지 않았으며 새 네트워크 호출·민감정보 로그·Any/dict/print 사용을 추가하지 않음.
- 반영: 테스트·문서 전용 커밋으로 origin/main에 fast-forward 푸시. `[skip render]`로 불필요한 애플리케이션 재배포를 건너뜀; 운영 코드는 9절에서 검증한 배포와 동일.
