"""Pure validation and classification. No predicted savings or inferred intent."""
from datetime import date


class InboxError(ValueError):
    """A named, user-correctable input or output failure."""


FIELDS = {"id", "title", "synthetic", "decision_required", "decision_reason",
          "alternatives", "missing_information", "next_action", "effort_minutes",
          "created_on", "reference_date"}


def validate_task(task):
    if not isinstance(task, dict):
        raise InboxError("SchemaError: record must be an object")
    unknown = set(task) - FIELDS
    if unknown:
        raise InboxError("SchemaError: unknown field(s): " + ", ".join(sorted(unknown)))
    for field in ("id", "title", "synthetic", "decision_required"):
        if field not in task:
            raise InboxError(f"SchemaError: missing field {field}")
    for field in ("id", "title", "decision_reason", "next_action"):
        if field in task:
            value = task[field]
            if not isinstance(value, str) or len(value) > 10000 or (field in ("id", "title") and not value.strip()):
                raise InboxError(f"SchemaError: {field} must be nonempty where required, text <= 10000 characters")
    for field in ("synthetic", "decision_required"):
        if type(task[field]) is not bool:
            raise InboxError(f"SchemaError: {field} must be boolean")
    if task["decision_required"] and not task.get("decision_reason", "").strip():
        raise InboxError("SchemaError: decision_reason required when decision_required is true")
    for field in ("alternatives", "missing_information"):
        values = task.get(field, [])
        if not isinstance(values, list) or len(values) > 100 or any(not isinstance(v, str) or not v.strip() or len(v) > 10000 for v in values):
            raise InboxError(f"SchemaError: {field} must be a list of at most 100 nonempty strings <= 10000 characters")
        if len(set(values)) != len(values):
            raise InboxError(f"SchemaError: {field} contains duplicates")
    if "effort_minutes" in task and (type(task["effort_minutes"]) is not int or not 0 <= task["effort_minutes"] <= 1000000):
        raise InboxError("SchemaError: effort_minutes must be an integer from 0 to 1000000 (user supplied, not measured)")
    if "created_on" in task or "reference_date" in task:
        for field in ("created_on", "reference_date"):
            try:
                value = task[field]
                if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except (KeyError, ValueError, TypeError):
                raise InboxError(f"SchemaError: {field} must be an ISO YYYY-MM-DD date; both dates required") from None
        if task["created_on"] > task["reference_date"]:
            raise InboxError("SchemaError: created_on is after reference_date (future creation date)")
    return dict(task)


def classify(task):
    task = validate_task(task)
    reasons = []
    if task["decision_required"]:
        reasons.append("declared decision: " + task["decision_reason"])
    if len(task.get("alternatives", [])) >= 2:
        reasons.append("two or more explicit alternatives")
    if task.get("missing_information"):
        reasons.append("explicit missing information")
    return {"task": task, "queue": "decision" if reasons else "execution", "reasons": reasons,
            "action_ready": not reasons and bool(task.get("next_action", "").strip())}


def compute(tasks):
    rows = []
    ids = set()
    for task in tasks:
        row = classify(task)
        task_id = row["task"]["id"]
        if task_id in ids:
            raise InboxError(f"SchemaError: duplicate id {task_id}")
        ids.add(task_id)
        rows.append(row)
    rows.sort(key=lambda r: r["task"]["id"])
    decisions = sum(r["queue"] == "decision" for r in rows)
    synthetic = sum(r["task"]["synthetic"] for r in rows)
    ready = sum(r["action_ready"] for r in rows)
    return {"schema_version": 1, "counts": {"total": len(rows), "decision": decisions,
            "execution": len(rows) - decisions, "action_ready": ready,
            "execution_needs_next_action": len(rows) - decisions - ready,
            "synthetic": synthetic, "real_user_entered": len(rows) - synthetic}, "records": rows,
            "honesty": "Counts computed from inputs. Effort is user supplied and unmeasured. Time saved and money saved are unmeasured and not reported."}
