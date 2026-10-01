"""Labelled deterministic fixtures. No randomness; no model or network calls."""
from .report import json_text


def fixture_tasks():
    tasks = []
    for i in range(200):
        group = i // 40
        task = {"id": f"task-{i + 1:03d}", "title": f"Synthetic task {i + 1}",
                "synthetic": True, "decision_required": group == 0,
                "next_action": "Send the prepared checklist" if group >= 3 else "",
                "created_on": "2026-09-30", "reference_date": "2026-09-30"}
        if group == 0:
            task["decision_reason"] = "Choose an application priority"
        if group == 1:
            task["alternatives"] = ["School revision", "Outreach follow-up"]
        if group == 2:
            task["missing_information"] = ["Confirm the application deadline"]
        tasks.append(task)
    return tasks


def expectations():
    # Hand-computed: 3 blocks of 40 decisions, 2 blocks of 40 ready executions.
    # Literal counts and independently enumerated IDs are never used by the engine.
    return {"synthetic": True, "label": "SYNTHETIC HAND-COMPUTED EXPECTATIONS",
            "counts": {"total": 200, "decision": 120, "execution": 80, "action_ready": 80,
                       "execution_needs_next_action": 0, "synthetic": 200, "real_user_entered": 0},
            "decision_ids": [f"task-{i:03d}" for i in range(1, 121)],
            "execution_ids": [f"task-{i:03d}" for i in range(121, 201)]}


def fixture_files():
    tasks = fixture_tasks()
    # Hand-written realistic examples, all synthetic, not Henry's actual tasks.
    tiny = [
        {"id": "tiny-1", "title": "Choose the first university application",
         "synthetic": True, "decision_required": True,
         "decision_reason": "Choose which application to prioritise"},
        {"id": "tiny-2", "title": "Allocate the evening work block",
         "synthetic": True, "decision_required": False,
         "alternatives": ["Revise chemistry", "Prepare outreach"]},
        {"id": "tiny-3", "title": "Prepare a client quotation",
         "synthetic": True, "decision_required": False,
         "missing_information": ["Client's agreed scope"]},
        {"id": "tiny-4", "title": "Send the approved outreach follow-up",
         "synthetic": True, "decision_required": False,
         "next_action": "Send the already approved draft"},
        {"id": "tiny-5", "title": "Upload the completed school assignment",
         "synthetic": True, "decision_required": False,
         "next_action": "Upload the finished PDF to the school portal"},
    ]
    return {"tasks.jsonl": "# SYNTHETIC FIXTURES: 200 records, deterministic, no random seed needed\n" +
            "".join(json_text(t).replace("\n", "") + "\n" for t in tasks),
            "expectations.json": json_text(expectations()),
            "tiny/tasks.jsonl": "# SYNTHETIC: five hand-written realistic cases, one from each block\n" +
            "".join(json_text(t).replace("\n", "") + "\n" for t in tiny),
            "README.md": "<!-- SYNTHETIC FIXTURE SET -->\n# Synthetic fixtures\n\nAll tasks and expectations are synthetic. Run the parent directory for 200 records or tiny/ for five.\n"}
