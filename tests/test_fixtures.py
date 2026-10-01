import json
from decision_inbox.cli import load_tasks, main
from decision_inbox.core import compute
from decision_inbox.fixtures import expectations, fixture_tasks


def test_fixtures_labelled_synthetic(dataset):
    for path in dataset.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".jsonl":
            assert content.startswith("# SYNTHETIC")
            assert all(json.loads(line)["synthetic"] is True for line in content.splitlines() if not line.startswith("#"))
        elif path.suffix == ".json":
            assert json.loads(content)["synthetic"] is True
            assert "SYNTHETIC" in json.loads(content)["label"]
        else:
            assert "SYNTHETIC" in content


def test_fixture_ground_truth_matches_hand_computed(dataset):
    tasks = load_tasks(dataset)
    assert len(tasks) == 200
    assert tasks == fixture_tasks()
    expected = json.loads((dataset / "expectations.json").read_text())
    assert expected == expectations()
    assert compute(tasks)["counts"] == expected["counts"]
    assert expected["counts"]["decision"] == 40 + 40 + 40
    assert expected["counts"]["execution"] == 40 + 40


def test_tiny_fixture(dataset):
    result = compute(load_tasks(dataset / "tiny"))
    assert result["counts"]["total"] == 5
    assert result["counts"]["decision"] == 3
    assert result["counts"]["execution"] == 2


def test_corrupted_task_changes_computed_counts(dataset, tmp_path, capsys):
    path = dataset / "tasks.jsonl"
    lines = path.read_text().splitlines()
    task = json.loads(lines[1])
    task["decision_required"] = False
    task["next_action"] = "Execute now"
    lines[1] = json.dumps(task)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = compute(load_tasks(dataset))
    assert result["counts"]["decision"] == 119
    assert result["counts"]["execution"] == 81
    assert result["counts"] != expectations()["counts"]
    state = tmp_path / "changed.json"
    assert main(["run", "--input", str(dataset), "--state", str(state)]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json", "--state", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["counts"] == result["counts"]


def test_expectations_are_not_engine_input(dataset):
    (dataset / "expectations.json").write_text('{"synthetic": true, "counts": {"total": 999}}')
    assert compute(load_tasks(dataset))["counts"]["total"] == 200
