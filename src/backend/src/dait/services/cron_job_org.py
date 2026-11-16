"""cron-job.org REST API 최소 클라이언트.

외부 예약 job 생성/수정/삭제만 담당한다. API 키와 tick 비밀값은 예외 메시지에 넣지 않는다.
"""

import httpx


class CronJobOrgError(Exception):
    """cron-job.org API 호출 실패. status_code만 담고 응답 본문/비밀값은 담지 않는다."""

    def __init__(self, status_code: int) -> None:
        """실패 상태 코드를 보관한다.

        입력: status_code (HTTP 상태, 네트워크 실패는 0)
        출력: 없음
        기능: 호출부가 404(이미 없음)와 그 외 실패를 구분하게 한다.
        """
        self.status_code = status_code
        super().__init__(f"cron-job.org request failed ({status_code})")


class CronJobOrgClient:
    """cron-job.org /jobs 엔드포인트 호출기."""

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.cron-job.org",
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """API 키와 기본 주소로 클라이언트를 만든다.

        입력: api_key (Bearer 토큰), api_url (https 기본 주소), timeout_seconds,
              transport (테스트용)
        출력: 없음
        기능: 모든 요청에 Authorization/JSON 헤더를 붙인다.
        """
        self._client = httpx.Client(
            base_url=api_url.rstrip("/") + "/",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        """HTTP 연결을 닫는다."""
        self._client.close()

    def __enter__(self) -> "CronJobOrgClient":
        """컨텍스트 매니저 진입."""
        return self

    def __exit__(self, *args: object) -> None:
        """컨텍스트 매니저 종료 시 연결을 닫는다."""
        self.close()

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> httpx.Response:
        """JSON 요청을 보내고 2xx만 통과시킨다."""
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as exc:
            raise CronJobOrgError(0) from exc
        if response.status_code >= 400:
            raise CronJobOrgError(response.status_code)
        return response

    def create_job(self, job: dict[str, object]) -> int:
        """새 cron job을 만들고 jobId를 돌려준다.

        입력: job (cron-job.org DetailedJob 페이로드)
        출력: int (생성된 jobId)
        기능: PUT /jobs. url만 필수지만 schedule/extendedData를 함께 보낸다.
        """
        response = self._request("PUT", "jobs", {"job": job})
        try:
            data = response.json()
            return int(data["jobId"])
        except (ValueError, KeyError, TypeError) as exc:
            raise CronJobOrgError(response.status_code) from exc

    def update_job(self, job_id: int, job: dict[str, object]) -> None:
        """기존 cron job을 부분 수정한다.

        입력: job_id (cron-job.org jobId), job (바꿀 필드만)
        출력: 없음
        기능: PATCH /jobs/{id}. 없는 job이면 CronJobOrgError(404).
        """
        self._request("PATCH", f"jobs/{job_id}", {"job": job})

    def delete_job(self, job_id: int) -> bool:
        """cron job을 삭제한다. 이미 없으면 False를 돌려준다.

        입력: job_id (cron-job.org jobId)
        출력: bool (삭제했으면 True, 404였으면 False)
        기능: DELETE /jobs/{id}.
        """
        try:
            response = self._client.request("DELETE", f"jobs/{job_id}")
        except httpx.HTTPError as exc:
            raise CronJobOrgError(0) from exc
        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            raise CronJobOrgError(response.status_code)
        return True
