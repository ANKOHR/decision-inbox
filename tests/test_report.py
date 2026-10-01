import json
from decision_inbox.cli import load_result
from decision_inbox.core import compute
from decision_inbox.fixtures import expectations, fixture_tasks
from decision_inbox.report import render


def test_report_matches_ground_truth_exact(state):
    result = json.loads(render(load_result(state), "json"))
    expected = expectations()
    assert result["counts"] == expected["counts"]
    for queue in ("decision", "execution"):
        assert [r["task"]["id"] for r in result["records"] if r["queue"] == queue] == expected[queue + "_ids"]


def test_report_zero_false_positives():
    result = compute(fixture_tasks())
    predicted = {r["task"]["id"] for r in result["records"] if r["queue"] == "decision"}
    ground_truth = set(expectations()["decision_ids"])
    assert predicted - ground_truth == set()
    assert ground_truth - predicted == set()


def test_report_carries_provenance_banner(state):
    for format in ("md", "json"):
        report = render(load_result(state), format)
        assert "Data provenance:" in report
        assert "200 synthetic fixture records" in report
        assert "0 real records entered by the user" in report
        assert "tasks.jsonl" in report


def test_hypothetical_figures_labelled(task):
    result = compute([{**task, "effort_minutes": 25}])
    for format in ("md", "json"):
        report = render(result, format)
        assert "unmeasured" in report
        assert "Time saved and money saved are unmeasured and not reported" in report
        assert "user supplied" in report
    assert "time_saved" not in result["counts"]


def test_no_em_dashes_in_outputs(task):
    value = {**task, "title": "A" + chr(0x2014) + "B"}
    result = compute([value])
    for format in ("md", "json"):
        assert chr(0x2014) not in render(result, format)
    assert json.loads(render(result, "json"))["records"][0]["task"]["title"] == value["title"]


def test_mixed_provenance(task):
    report = render(compute([task, {**task, "id": "fixture", "synthetic": True}]))
    assert "1 synthetic fixture records" in report
    assert "1 real records entered by the user" in report
