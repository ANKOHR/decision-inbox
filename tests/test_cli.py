import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from decision_inbox.cli import atomic_write, load_result, main
from decision_inbox.core import InboxError
from conftest import write_task


def test_run_completes_on_fixture(dataset, tmp_path, capsys):
    start = time.perf_counter()
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(dataset), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state)]) == 0
    assert time.perf_counter() - start < 5
    assert "Traceback" not in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    directory = tmp_path / "empty"
    directory.mkdir()
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(directory), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state)]) == 0
    assert load_result(state)["counts"]["total"] == 0
    assert "Data provenance:" in capsys.readouterr().out


@pytest.mark.parametrize("content,error", [('not json', 'ParseError'), ('{"id":', 'ParseError'),
    ('{"id":"a","id":"b"}', 'SchemaError'), ('[]', 'SchemaError')])
def test_malformed_input_named_error(tmp_path, capsys, content, error):
    directory = tmp_path / "bad"
    directory.mkdir()
    path = directory / "broken.jsonl"
    path.write_text("# comment\n" + content, encoding="utf-8")
    assert main(["run", "--input", str(directory), "--state", str(tmp_path / "state.json")]) == 2
    stderr = capsys.readouterr().err
    assert error in stderr and "broken.jsonl" in stderr and "line 2" in stderr
    assert "Traceback" not in stderr


def test_determinism_byte_identical(dataset, tmp_path):
    state = tmp_path / "state.json"
    args = ["run", "--input", str(dataset), "--state", str(state)]
    assert main(args) == 0
    before = state.read_bytes()
    assert main(args) == 0
    assert state.read_bytes() == before
    report = tmp_path / "report.md"
    args = ["report", "--state", str(state), "--out", str(report)]
    assert main(args) == 0
    before = report.read_bytes()
    assert main(args) == 0
    assert report.read_bytes() == before


def test_cli_smoke_all_subcommands(state, capsys):
    for command in ("fixtures", "run", "report", "triage", "next"):
        result = subprocess.run([sys.executable, "-m", "decision_inbox.cli", command, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Example:" in result.stdout
    assert main(["triage", "--state", str(state), "--queue", "decision"]) == 0
    assert main(["next", "--state", str(state), "--id", "task-121"]) == 0
    assert main(["report", "--state", str(state), "--format", "json"]) == 0
    assert main(["next", "--state", str(state), "--id", "unknown"]) == 2


def test_missing_input_and_state_named(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "absent")]) == 2
    assert "MissingInputError" in capsys.readouterr().err
    assert main(["report", "--state", str(tmp_path / "absent.json")]) == 2
    assert "MissingResultError" in capsys.readouterr().err


def test_schema_error_names_field_file_and_line(tmp_path, task, capsys):
    write_task(tmp_path, {**task, "effort_minutes": -1})
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "effort_minutes" in error and "tasks.jsonl" in error and "line 1" in error


def test_failed_run_preserves_previous_result(dataset, state, capsys):
    before = state.read_bytes()
    (dataset / "tasks.jsonl").write_text("bad json")
    assert main(["run", "--input", str(dataset), "--state", str(state)]) == 2
    assert state.read_bytes() == before


def test_report_write_failure_no_partial_files(state, tmp_path, capsys):
    output = tmp_path / "directory"
    output.mkdir()
    before = set(tmp_path.iterdir())
    assert main(["report", "--state", str(state), "--out", str(output)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before


def test_atomic_write_failure_preserves_existing_file(tmp_path, monkeypatch):
    output = tmp_path / "report.md"
    output.write_text("original")
    def fail(*args):
        raise OSError("planted replace failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(InboxError, match="WriteError"):
        atomic_write(output, "new")
    assert output.read_text() == "original"
    assert list(tmp_path.iterdir()) == [output]


def test_tampered_state_named_error(state, capsys):
    data = json.loads(state.read_text())
    data["counts"]["total"] = 999
    state.write_text(json.dumps(data))
    assert main(["report", "--state", str(state)]) == 2
    assert "ResultError" in capsys.readouterr().err


def test_unicode_round_trip_and_provenance(tmp_path, task, capsys):
    directory = tmp_path / "å­¦æ ¡"
    value = {**task, "title": "cafÃ© å­¦æ ¡ " + "a" * 9000 + chr(0x2014),
             "next_action": r"Open C:\Users\henry\Documents\file"}
    write_task(directory, value)
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(directory), "--state", str(state)]) == 0
    assert load_result(state)["records"][0]["task"] == value
    assert load_result(state)["sources"][task["id"]] == {"file": "tasks.jsonl", "line": 1, "synthetic": False}
    assert main(["report", "--state", str(state)]) == 0
    assert chr(0x2014) not in capsys.readouterr().out


def test_duplicate_ids_across_files(tmp_path, task, capsys):
    write_task(tmp_path, task)
    (tmp_path / "other.jsonl").write_text(json.dumps(task))
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "duplicate id" in capsys.readouterr().err


def test_unsupported_format_named(tmp_path, capsys):
    (tmp_path / "bad.csv").write_text("a,b\n1,2")
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "unsupported file format" in capsys.readouterr().err


def test_fixtures_do_not_overwrite(dataset, capsys):
    before = (dataset / "tasks.jsonl").read_bytes()
    assert main(["fixtures", "--out", str(dataset)]) == 2
    assert (dataset / "tasks.jsonl").read_bytes() == before


def test_invalid_utf8_names_actual_line(tmp_path, capsys):
    (tmp_path / "broken.jsonl").write_bytes(b"# comment\n\xff")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "broken.jsonl" in error and "line 2" in error
