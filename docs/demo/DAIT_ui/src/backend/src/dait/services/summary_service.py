"""기존 요약 API를 공통 백그라운드 작업자에 연결합니다."""
from dait.services import summary_worker as worker

MODEL = worker.MODEL


def start(article_id, article):
    return worker.request(article_id)


def start_batch():
    return worker.request()


def get(job_id):
    if job_id == "background-batch":
        return worker.batch_status()
    return worker.get(job_id)


def batch_status():
    return worker.batch_status()
