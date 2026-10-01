"""Measure the actual installed CLI end-to-end; synthetic agreement is not real accuracy."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time


def main():
    command = shutil.which("di")
    if not command:
        executable = Path(sysconfig.get_path("scripts", scheme="nt_user")) / "di.exe"
        if not executable.is_file():
            raise SystemExit("Install the local package first; installed di executable not found")
        command = str(executable)
    with tempfile.TemporaryDirectory(prefix="di-demo-") as temporary:
        directory = Path(temporary)
        inputs = directory / "demo"
        state = directory / "state.json"
        report_path = directory / "report.json"
        start = time.perf_counter()
        invocations = [
            [command, "fixtures", "--out", str(inputs)],
            [command, "run", "--input", str(inputs), "--state", str(state)],
            [command, "report", "--format", "md", "--state", str(state)],
        ]
        for invocation in invocations:
            completed = subprocess.run(invocation, capture_output=True, encoding="utf-8", check=True)
            assert "Traceback" not in completed.stdout + completed.stderr
        seconds = time.perf_counter() - start
        assert seconds < 5, f"Demo exceeded five seconds: {seconds}"
        result = json.loads(state.read_text(encoding="utf-8"))
        expected = json.loads((inputs / "expectations.json").read_text(encoding="utf-8"))
        assert result["counts"] == expected["counts"]
        actual_ids = {r["task"]["id"] for r in result["records"] if r["queue"] == "decision"}
        expected_ids = set(expected["decision_ids"])
        assert actual_ids == expected_ids
        start = time.perf_counter()
        subprocess.run([command, "report", "--format", "json", "--state", str(state),
                        "--out", str(report_path)], capture_output=True, encoding="utf-8", check=True)
        report_seconds = time.perf_counter() - start
        assert report_seconds < 5
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["counts"] == expected["counts"]
        assert "Data provenance:" in report["provenance_banner"]
        print(json.dumps({"synthetic": True, "records": 200, "counts": result["counts"],
                          "false_positives": len(actual_ids - expected_ids),
                          "missed_decisions": len(expected_ids - actual_ids),
                          "demo_seconds_measured": round(seconds, 6),
                          "report_seconds_measured": round(report_seconds, 6),
                          "time_saved": "unmeasured; no manual baseline",
                          "real_use_accuracy": "unmeasured"}, indent=2))


if __name__ == "__main__":
    main()
