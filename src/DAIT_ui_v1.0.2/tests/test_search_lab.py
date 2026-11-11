"""브라우저 유사도 작업 API를 모델 다운로드 없이 점검합니다."""
import http.client
import json
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend import news as app
from backend.services import search_lab_service as service


class LabTests(unittest.TestCase):
    # 기능: 통합 검색 전 색인 생성 순서 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_integrated_builds_before_search(self):
        calls = []
        backend = SimpleNamespace(build=lambda *a, **kw: calls.append("build"),
                                  evaluate=lambda *a, **kw: calls.append("evaluate") or {"hybrid": []})
        with patch.object(service, "_jobs", {}), patch.object(service, "_encoder_bundle", (object(), "version")), patch.object(service, "engine", return_value=backend):
            job_id = service.start("integrated", "반도체", 0.35, None)
            deadline = time.monotonic() + 2
            while service.get(job_id, None)["status"] == "running" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(service.get(job_id, None)["status"], "completed")
            self.assertEqual(calls, ["build", "evaluate"])

    # 기능: 검색 작업 소유자와 결과 접근 제한 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_job_owner_and_result(self):
        backend = SimpleNamespace(evaluate=lambda *args, **kwargs: {"keyword": [], "semantic": [], "hybrid": []})
        with patch.object(service, "_jobs", {}), patch.object(service, "_encoder_bundle", (object(), "version")), patch.object(service, "engine", return_value=backend), patch.object(service, "INDEX_DB", SimpleNamespace(is_file=lambda: True)):
            job_id = service.start("compare", "반도체", 0.35, "user1")
            deadline = time.monotonic() + 2
            while service.get(job_id, "user1")["status"] == "running" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(service.get(job_id, "user1")["status"], "completed")
            self.assertIsNone(service.get(job_id, "user2"))

    # 기능: 화면 및 API 요청 검증 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_page_and_api_validation(self):
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port)
        try:
            client.request("GET", "/search-lab")
            response = client.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            client.request("GET", "/api/search-lab/info", headers={"Cookie": "dait_user=user2"})
            response = client.getresponse()
            self.assertEqual(json.loads(response.read())["user"], "user2")
            client.request("POST", "/api/search-lab/jobs", body=json.dumps({"action": "compare", "query": ""}), headers={"Content-Type": "application/json"})
            response = client.getresponse()
            self.assertEqual(response.status, 400)
            response.read()
            job = {"status": "completed", "result": {"query": "반도체", "user": "user2", "hybrid": [{"id": "x", "cosine": 0.7845}]}}
            article = ("제목", "출처", "2026-11-09", "설명", "", "https://example.com", 0, "보안")
            with patch.object(service, "get", return_value=job), patch.object(app, "get_article", return_value=article):
                client.request("GET", "/?q=%EB%B0%98%EB%8F%84%EC%B2%B4&search_job=test", headers={"Cookie": "dait_user=user2"})
                response = client.getresponse()
                output = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertIn("의미 유사도", output)
                self.assertIn("<strong>0.784</strong>", output)
                self.assertIn("키워드와 의미 유사도 결합순", output)
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
