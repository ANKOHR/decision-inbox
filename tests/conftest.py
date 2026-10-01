import json
from pathlib import Path
import pytest
from decision_inbox.cli import main


@pytest.fixture
def task():
    return {"id": "real-1", "title": "Send approved email", "synthetic": False,
            "decision_required": False, "next_action": "Send the approved draft"}


@pytest.fixture
def dataset(tmp_path):
    directory = tmp_path / "fixtures"
    assert main(["fixtures", "--out", str(directory)]) == 0
    return directory


@pytest.fixture
def state(dataset, tmp_path):
    path = tmp_path / "state.json"
    assert main(["run", "--input", str(dataset), "--state", str(path)]) == 0
    return path


def write_task(directory, task):
    directory.mkdir(exist_ok=True)
    (directory / "tasks.jsonl").write_text(json.dumps(task, ensure_ascii=False) + "\n", encoding="utf-8")
