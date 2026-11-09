# 뉴스 검색 설치 및 실행 안내

이 프로젝트는 RSS 뉴스 기사를 수집해 벡터 데이터베이스에 저장하고, 검색어와 의미가 비슷한 기사를 웹에서 보여줍니다.

## 1. 다른 PC로 프로젝트 옮기기

다음 파일과 폴더를 같은 구조로 복사합니다.

```text
프로젝트 폴더/
├── db_search.py
├── webapp.py
├── requirement.txt
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

기존 기사도 가져오려면 원본 PC에서 프로그램을 종료한 후 `news_db/` 폴더를 함께 복사합니다. 복사하지 않으면 새 PC에서 기사를 다시 수집할 수 있습니다. `.venv/`는 PC마다 새로 만드세요. 모델 캐시는 패키지나 `news_db/`에 포함되지 않으므로 아래에서 별도로 준비합니다.

## 2. Python과 패키지 설치

Python 3.13이 설치되어 있어야 합니다. 기존 환경에 설치된 직접 의존성 버전을 `requirement.txt`에 기록했습니다. 인터넷 연결 후 프로젝트 폴더에서 터미널을 열어 다음을 실행하세요.

### Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirement.txt
```

이후 안내의 `python` 대신 `.\.venv\Scripts\python.exe`를 사용하거나 다음 명령으로 가상 환경을 활성화하세요.

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 때문에 활성화할 수 없다면 정책을 변경할 필요 없이 위의 `.\.venv\Scripts\python.exe` 경로를 사용하면 됩니다.

### macOS / Linux

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirement.txt
```

패키지 설치 시 PyTorch 등 필요한 하위 패키지도 함께 설치됩니다. 환경에 따라 설치에 시간과 디스크 공간이 필요할 수 있습니다.

## 3. 검색 모델 다운로드

두 Python 파일은 `intfloat/multilingual-e5-small` 모델을 `local_files_only=True`로 불러오므로 새 PC에서는 먼저 모델을 로컬 캐시에 내려받아야 합니다. 인터넷이 연결된 상태에서 **위 가상 환경을 활성화한 뒤** 한 번 실행하세요.

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
```

Windows에서 가상 환경을 활성화하지 않았다면 `python` 대신 `.\.venv\Scripts\python.exe`를 사용합니다. 모델 다운로드에 실패하면 인터넷 연결과 모델 접근 가능 여부를 확인하세요. 이후 앱을 실행하는 같은 사용자 계정에서 모델 캐시를 사용해야 합니다.

## 4. 기사 수집: `db_search.py`

프로젝트 폴더에서 다음을 실행합니다. RSS 피드에 접근할 수 있도록 인터넷이 필요합니다.

```bash
python db_search.py
```

이 파일은 다음 순서로 동작합니다.

1. `news_db/`의 ChromaDB와 로컬 검색 모델을 엽니다.
2. `FEEDS`에 정의된 뉴스 RSS에서 제목, 주소, 요약, 발행 시각을 읽습니다.
3. 기사 URL의 SHA-256 해시를 ID로 사용해 기존 기사 및 같은 수집 중 중복을 제외합니다.
4. 제목과 요약으로 정규화된 임베딩을 만들고 기사 정보 및 수집 시각과 함께 저장합니다.
5. 마지막 수집 완료 시각과 전체 소요 시간을 컬렉션 메타데이터에 기록합니다. 새 기사가 없어도 수집 완료 시각은 갱신됩니다.

기존 DB를 지우고 처음부터 다시 수집하려면 아래 명령을 사용합니다. **`news_db/` 전체가 삭제되므로 기존 기사가 필요하면 먼저 백업하고 웹 서버를 종료하세요.**

```bash
python db_search.py --reset
```

수집된 기사가 없으면 RSS 주소의 접속 상태와 터미널 출력을 확인하세요. 기존 기사는 개별 수집 시각이 저장되지 않았을 수 있으며 화면에 `기록 없음`으로 표시됩니다.

## 5. 웹 앱 실행: `webapp.py`

```bash
python webapp.py
```

브라우저에서 <http://127.0.0.1:5000>에 접속합니다. 검색어와 기사 수 1~50개를 선택하여 검색하세요. 종료하려면 서버가 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.

이 파일은 시작할 때 ChromaDB와 로컬 모델을 불러오고, 첫 검색 지연을 줄이기 위해 모델을 미리 실행합니다.

- `/`: 저장 기사 수, 수집 정보, 저장된 기사 최대 10개를 HTML 화면에 표시합니다.
- `/search`: 검색어와 기사 수를 검증하고, 검색어 임베딩으로 유사 기사를 조회하여 JSON으로 반환합니다. 저장된 기사보다 많이 요청하면 실제 저장된 수만큼만 반환합니다.
- 결과의 유사도는 정규화된 벡터의 코사인 유사도를 0~100% 범위로 표시한 상대적 지표입니다. 정답 확률은 아닙니다. 발행 및 수집 시각은 화면에서 한국 시간으로 표시합니다.
- 검색 소요 시간은 서버에서 임베딩 생성과 DB 조회에 걸린 시간입니다. 수집 소요 시간은 모델 준비, RSS 읽기, 임베딩과 저장을 포함합니다.

화면은 `templates/index.html`, `static/style.css`, `static/app.js`로 구성됩니다. 개발 서버는 로컬 테스트용입니다.
