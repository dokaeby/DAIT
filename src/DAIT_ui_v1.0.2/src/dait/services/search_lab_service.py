"""브라우저에서 요청한 임베딩 색인·비교 작업을 순차 실행합니다."""
import importlib
import sys
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace

from dait.core.config import INDEX_DB
from dait.core.config import EMBEDDING_MODEL as MODEL
_lock = threading.Lock()
_jobs = {}
_encoder_bundle = None


# 기능: 검색 비교 파이프라인을 필요할 때 로드한다.
# 입력: 없음.
# 출력: dait.pipelines.search_compare 모듈.
def engine():
    return importlib.import_module("dait.pipelines.search_compare")


# 기능: 검색 조건을 검증하고 색인·비교 작업을 백그라운드에서 시작한다.
# 입력:
#   action: 실행할 작업 종류 또는 작업 시작 콜백.
#   query: 검색어 문자열.
#   threshold: 최소 코사인 유사도(-1~1).
#   user: 현재 사용자 이름(비로그인은 None).
#   category: 필터 카테고리(빈 문자열이면 전체).
#   interests: 사용자 관심 카테고리(없으면 기본 관심사 사용).
# 출력: 작업 ID 문자열. 잘못된 조건 또는 동시 실행 시 예외.
def start(action, query, threshold, user, category="", interests=None):
    if action not in ("build", "compare", "integrated"):
        raise ValueError("알 수 없는 작업입니다.")
    if action in ("compare", "integrated") and not query.strip():
        raise ValueError("검색어를 입력하세요.")
    if len(query) > 200 or not -1 <= threshold <= 1:
        raise ValueError("검색어는 200자 이하, 최소 유사도는 -1부터 1까지여야 합니다.")
    with _lock:
        if any(job["status"] == "running" for job in _jobs.values()):
            raise RuntimeError("다른 색인·비교 작업이 진행 중입니다. 완료 후 다시 시도해 주세요.")
        while len(_jobs) >= 20:
            del _jobs[next(iter(_jobs))]
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"owner": user, "status": "running", "message": "작업을 준비하고 있습니다.", "result": None}
    selected = tuple(interests) if interests is not None else None
    threading.Thread(target=_run, args=(job_id, action, query, threshold, user, category, selected), daemon=True).start()
    return job_id


# 기능: 요청한 색인·비교 작업을 실행하고 메모리의 진행 상태를 갱신한다.
# 입력:
#   job_id: 작업 식별자.
#   action: 실행할 작업 종류 또는 작업 시작 콜백.
#   query: 검색어 문자열.
#   threshold: 최소 코사인 유사도(-1~1).
#   user: 현재 사용자 이름(비로그인은 None).
#   category: 필터 카테고리(빈 문자열이면 전체).
#   interests: 사용자 관심 카테고리(없으면 기본 관심사 사용).
# 출력: None. 성공 결과 또는 오류를 작업 사전에 기록한다.
def _run(job_id, action, query, threshold, user, category="", interests=None):
    global _encoder_bundle
    # 기능: 현재 검색 작업의 진행 안내 문구를 잠금 아래 갱신한다.
    # 입력:
    #   message: 표시할 진행 안내 문구.
    # 출력: None.
    def update(message):
        with _lock:
            _jobs[job_id]["message"] = message
    try:
        backend = engine()
        if action == "compare" and not INDEX_DB.is_file():
            raise ValueError("색인이 없습니다. 먼저 ‘색인 준비·갱신’을 눌러 주세요.")
        if _encoder_bundle is None:
            update("모델을 준비하고 있습니다. 최초 다운로드와 CPU 로드에는 시간이 걸릴 수 있습니다.")
            _encoder_bundle = backend.load_encoder(MODEL)
        args = SimpleNamespace(model=MODEL, revision="main", offline=False, status=False, force=False,
                               query=query, min_score=-1.0 if action == "integrated" else threshold, user=user, category=category, interests=interests)
        if action == "build":
            backend.build(args, encoder_bundle=_encoder_bundle, progress=update)
            result = {"message": "색인이 준비되었습니다. 검색어를 입력해 유사도를 확인하세요."}
        else:
            if action == "integrated":
                update("기사 임베딩을 준비하고 있습니다.")
                backend.build(args, encoder_bundle=_encoder_bundle, progress=update)
            update("검색어를 인코딩하고 기사별 유사도를 계산하고 있습니다.")
            result = backend.evaluate(args, encoder_bundle=_encoder_bundle)
        with _lock:
            _jobs[job_id].update(status="completed", message="완료되었습니다.", result=result)
    except Exception as exc:
        with _lock:
            _jobs[job_id].update(status="error", message=str(exc))


# 기능: 작업 소유자를 확인하고 외부에 공개할 상태를 조회한다.
# 입력:
#   job_id: 작업 식별자.
#   user: 현재 사용자 이름(비로그인은 None).
# 출력: 소유자 필드를 제외한 작업 사전 또는 None.
def get(job_id, user):
    with _lock:
        job = _jobs.get(job_id)
        if job is None or job["owner"] != user:
            return None
        return {key: value for key, value in job.items() if key != "owner"}
