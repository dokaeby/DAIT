"""프로젝트 경로와 SQLite 설정. 패키지 위치 변화와 독립적으로 기존 data를 사용합니다."""
import os
from pathlib import Path

# src/dait/core/config.py -> 프로젝트 루트
ROOT = Path(os.environ.get("DAIT_PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
DATA_DIR = ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
ASSETS_DIR = ROOT / "src" / "frontend" / "assets"
NEWS_DB = DATA_DIR / "real_articles.db"
SUMMARY_DB = DATA_DIR / "summary_tests.db"
TRANSLATION_DB = DATA_DIR / "foreign_translations.db"
INDEX_DB = DATA_DIR / "search_index.db"
QUEUE_DB = DATA_DIR / "summary_queue.db"
USER_DB = DATA_DIR / "users.db"
SUMMARY_MODEL = "qwen3:4b"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


# 기능: 데이터 및 보고서 저장 폴더를 준비한다.
# 입력: 없음.
# 출력: None. 필요한 디렉터리를 생성한다.
def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
