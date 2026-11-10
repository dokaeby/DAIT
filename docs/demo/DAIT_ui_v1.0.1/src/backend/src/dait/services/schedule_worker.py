"""예약 알림 작업자. 서버가 켜져 있는 동안 30초마다 예약 시각이 된 계정을 확인합니다."""

import logging
import sqlite3
import threading
from datetime import UTC, datetime

from dait.services import settings_service

logger = logging.getLogger(__name__)
CHECK_INTERVAL_SECONDS = 30


class ScheduleWorker:
    def __init__(self, interval: float = CHECK_INTERVAL_SECONDS) -> None:
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="dait-schedule", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def check_once(self) -> int:
        try:
            return settings_service.run_due_schedules(datetime.now(UTC))
        except (sqlite3.Error, OSError) as exc:
            # 한 번 실패해도 다음 확인에서 다시 시도합니다. 예약 시각은 last_run_at으로 지켜집니다.
            logger.error("예약 알림 확인 실패: %s", exc)
            return 0

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self.check_once()


worker = ScheduleWorker()
