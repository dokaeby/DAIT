"""이전 실행 위치에서 새 프런트엔드 패키지를 찾는 호환 경로."""
from pathlib import Path
__path__ = [str(Path(__file__).resolve().parent.parent / "src" / "frontend" / "src" / "frontend")]
