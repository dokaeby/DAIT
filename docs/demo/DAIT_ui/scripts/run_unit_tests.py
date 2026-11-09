"""Run all document-based checks, keep every failure, and write a traceability report."""

import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / ".tmp" / "test-results"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary_base = OUTPUT.parent / "pytest-runtime" / ("run-" + uuid.uuid4().hex)
    if not temporary_base.resolve().is_relative_to((ROOT / ".tmp").resolve()):
        raise RuntimeError("Temporary test path escaped project .tmp")
    if temporary_base.exists():
        raise RuntimeError("Temporary test path must be new")
    temporary_base.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, PYTHONUTF8="1", APP_ENV="test")
    commands = {
        "pytest": [
            "pytest",
            "tests/unit",
            "-q",
            f"--basetemp={temporary_base}",
            "--junitxml=.tmp/test-results/unit.xml",
            "--cov=dait",
            "--cov=frontend",
            "--cov-branch",
            "--cov-report=xml:.tmp/test-results/coverage.xml",
            "--cov-report=html:.tmp/coverage",
        ],
        "ruff-check": ["ruff", "check", ".", "--output-format=json"],
        "ruff-format": ["ruff", "format", "--check", "."],
        "pyright": ["pyright", "--pythonpath", sys.executable, "--outputjson"],
    }
    statuses = {}
    for name, arguments in commands.items():
        result = subprocess.run(
            [sys.executable, "-m", *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        extension = "json" if name in ("ruff-check", "pyright") else "log"
        (OUTPUT / f"{name}.{extension}").write_text(result.stdout, encoding="utf-8")
        (OUTPUT / f"{name}.stderr.log").write_text(result.stderr, encoding="utf-8")
        statuses[name] = result.returncode
        print(f"{name}: exit {result.returncode}", flush=True)
    (OUTPUT / "run-status.json").write_text(json.dumps(statuses, indent=2), encoding="utf-8")
    build_report(statuses)
    return int(any(statuses.values()))


def build_report(statuses):
    cases = json.loads((OUTPUT / "cases.json").read_text(encoding="utf-8"))
    document = (ROOT / "docs/testing/test-cases-v1.0.1.md").read_text(encoding="utf-8")
    ids = list(dict.fromkeys(re.findall(r"^### (UT-[A-Z]+-\d+)", document, re.MULTILINE)))
    matrix = []
    for case_id in ids:
        checks = [test for test in cases if case_id in test["ut_ids"]]
        missing = case_id.startswith(
            ("UT-SCH-", "UT-NOTI-", "UT-REL-", "UT-CACHE-")
        ) or case_id in {"UT-AUTH-004", "UT-AUTH-008", "UT-AUTH-009", "UT-AUTH-011", "UT-AUTH-012"}
        different = case_id.startswith("UT-SET-") or case_id in {
            "UT-HOME-007",
            "UT-HOME-008",
            "UT-HOME-009",
            "UT-HOME-010",
            "UT-HOME-011",
            "UT-DETAIL-001",
            "UT-DETAIL-003",
            "UT-DB-001",
            "UT-DB-003",
            "UT-DB-004",
            "UT-DB-005",
            "UT-DB-006",
            "UT-DB-007",
            "UT-DB-008",
            "UT-DB-009",
            "UT-DB-010",
        }
        outcome = (
            "FAIL"
            if any(t["outcome"] in ("failed", "error") for t in checks)
            else "CHECKED_PARTIALLY"
            if checks
            else "NOT_IMPLEMENTED"
            if missing
            else "DESIGN_DIFFERENCE"
            if different
            else "NOT_COVERED"
        )
        matrix.append(dict(id=case_id, status=outcome, tests=[t["nodeid"] for t in checks]))
    (OUTPUT / "traceability.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    passed = sum(c["outcome"] == "passed" for c in cases)
    failed = sum(c["outcome"] == "failed" for c in cases)
    skipped = sum(c["outcome"] == "skipped" for c in cases)
    errors = sum(c["outcome"] == "error" for c in cases)
    coverage = ET.parse(OUTPUT / "coverage.xml").getroot()
    report = [
        "# 자동 단위 테스트 실행 결과",
        "",
        f"테스트: 통과 {passed}, 실패 {failed}, 환경/수집 오류 {errors}, skip {skipped} / 전체 {len(cases)}.",
        "문서 전체 완료 판정: 미충족. 실행되지 않은 ID는 통과로 처리하지 않았습니다.",
        f"백엔드·서버 HTML Python 라인 커버리지: {float(coverage.attrib['line-rate']):.1%}.",
        f"분기 커버리지: {float(coverage.attrib['branch-rate']):.1%}.",
        "브라우저 JavaScript/CSS 동작 커버리지는 포함하지 않습니다.",
        "",
        "## 품질 게이트",
        "",
        *[f"- {name}: exit {code}" for name, code in statuses.items()],
        "",
        "## 실패 항목",
        "",
    ]
    for case in cases:
        if case["outcome"] in ("failed", "error"):
            report.append(f"- `{case['nodeid']}` — {', '.join(case['ut_ids']) or '기존 기능 회귀'}")
    report += [
        "",
        "## 문서 추적표",
        "",
        "CHECKED_PARTIALLY는 해당 ID의 일부 기대결과만 검사했다는 뜻이며 전체 PASS가 아닙니다.",
        "NOT_COVERED에는 미구현 기능과 아직 테스트를 작성하지 않은 항목이 포함됩니다. 세부 분류는 UNIT_TEST_GUIDE.md를 참고합니다.",
        "",
        "| 문서 ID | 판정 | 연결 테스트 수 |",
        "|---|---|---|",
    ]
    report += [f"| {row['id']} | {row['status']} | {len(row['tests'])} |" for row in matrix]
    report += [
        "",
        "## 격리 범위",
        "",
        "테스트마다 임시 DB·고정 clock·ID를 사용합니다. 실제 DB 접근, 외부 HTTP/SMTP, 모델 로드·다운로드 및 프로세스 실행을 차단합니다.",
        "Windows asyncio의 내부 wakeup socketpair 생성만 허용하며, TestClient는 인메모리 ASGI 전송을 사용합니다.",
        "테스트 의존성 설치와 정적 분석 도구 실행은 테스트 외부의 준비 단계입니다.",
        "이메일 인증 5단계 및 외부 AI API는 구현하지 않았습니다.",
    ]
    (OUTPUT / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Report: {OUTPUT / 'REPORT.md'}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
