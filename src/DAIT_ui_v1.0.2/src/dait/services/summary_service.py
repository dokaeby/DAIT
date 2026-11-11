"""기존 요약 API를 공통 백그라운드 작업자에 연결합니다."""
from dait.services import summary_worker as worker

MODEL = worker.MODEL


# 기능: 기사 요약 요청을 공용 작업자 대기열로 전달한다.
# 입력:
#   article_id: 기사 식별자.
#   article: 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
# 출력: 요약 작업 ID 문자열.
def start(article_id, article):
    return worker.request(article_id)


# 기능: 공용 작업자에 전체 기사 요약 처리를 요청한다.
# 입력: 없음.
# 출력: 배치 식별 문자열 background-batch.
def start_batch():
    return worker.request()


# 기능: 배치 식별자 또는 개별 작업 ID에 맞는 상태를 조회한다.
# 입력:
#   job_id: 작업 식별자.
# 출력: 상태 사전 또는 작업이 없으면 None.
def get(job_id):
    if job_id == "background-batch":
        return worker.batch_status()
    return worker.get(job_id)


# 기능: 공용 작업자의 전체 처리 상태를 조회한다.
# 입력: 없음.
# 출력: 배치 상태 사전.
def batch_status():
    return worker.batch_status()
