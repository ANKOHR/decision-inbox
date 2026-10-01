import pytest
from decision_inbox.core import InboxError, classify, compute


def test_explicit_signals(task):
    assert classify(task)["queue"] == "execution"
    assert classify(task)["action_ready"]
    for changes in ({"decision_required": True, "decision_reason": "Choose priority"},
                    {"alternatives": ["A", "B"]}, {"missing_information": ["Deadline"]}):
        assert classify({**task, **changes})["queue"] == "decision"


def test_missing_next_action_is_named(task):
    result = compute([{**task, "next_action": ""}])
    assert result["counts"]["execution_needs_next_action"] == 1
    assert result["counts"]["action_ready"] == 0


@pytest.mark.parametrize("changes,field", [
    ({"effort_minutes": -1}, "effort_minutes"),
    ({"effort_minutes": True}, "effort_minutes"),
    ({"effort_minutes": 1000001}, "effort_minutes"),
    ({"created_on": "2099-01-01", "reference_date": "2026-09-30"}, "created_on"),
    ({"created_on": "2026-02-30", "reference_date": "2026-09-30"}, "created_on"),
    ({"created_on": "20260930", "reference_date": "2026-09-30"}, "created_on"),
    ({"title": "x" * 10001}, "title"),
    ({"synthetic": "false"}, "synthetic"),
    ({"decision_required": True}, "decision_reason"),
    ({"alternatives": ["a", "a"]}, "alternatives"),
    ({"missing_information": [1]}, "missing_information"),
    ({"amount": -10}, "amount"),
])
def test_rejects_adversarial_values(task, changes, field):
    with pytest.raises(InboxError, match=field):
        compute([{**task, **changes}])


def test_duplicate_ids_rejected(task):
    with pytest.raises(InboxError, match="duplicate id"):
        compute([task, task])


def test_handles_unicode_and_long_inputs(task):
    value = {**task, "title": "学校 café " + "x" * 9000,
             "next_action": r"Open C:\Users\henry\Documents\applications"}
    result = compute([value])
    assert result["records"][0]["task"] == value


def test_counts_reconcile_with_mixed_provenance(task):
    result = compute([task, {**task, "id": "synthetic-2", "synthetic": True,
                            "decision_required": True, "decision_reason": "Pick"}])
    counts = result["counts"]
    assert counts["total"] == counts["decision"] + counts["execution"] == 2
    assert counts["synthetic"] + counts["real_user_entered"] == 2


def test_sorting_is_deterministic(task):
    other = {**task, "id": "a"}
    assert compute([task, other]) == compute([other, task])
