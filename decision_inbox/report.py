"""Deterministic report rendering with explicit provenance."""
import json


def safe_text(value):
    # Encode forbidden punctuation supplied by users without losing information.
    return value.replace(chr(0x2014), "\\u2014")


def json_text(value):
    return safe_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)) + "\n"


def banner(result):
    counts = result["counts"]
    summary = (f"Data provenance: {counts['synthetic']} synthetic fixture records; "
            f"{counts['real_user_entered']} real records entered by the user "
            "(as declared by input synthetic flags, not independently verified).")
    files = {}
    for source in result.get("sources", {}).values():
        counts_by_kind = files.setdefault(source["file"], {True: 0, False: 0})
        counts_by_kind[source["synthetic"]] += 1
    details = [json.dumps(name, ensure_ascii=False) + f": {kinds[True]} synthetic, {kinds[False]} real user-entered"
               for name, kinds in sorted(files.items())]
    return summary + (" Inputs: " + "; ".join(details) + "." if details else "")


def render(result, format="md"):
    if format == "json":
        return json_text({**result, "provenance_banner": banner(result)})
    lines = ["# Decision Inbox", "", banner(result), "", result["honesty"], "",
             "## Computed counts", ""]
    lines.extend(f"- {key}: {value}" for key, value in result["counts"].items())
    for queue in ("decision", "execution"):
        lines.extend(["", "## " + queue.title() + " queue", ""])
        for row in result["records"]:
            if row["queue"] != queue:
                continue
            task = row["task"]
            # JSON quoting prevents titles and multiline input becoming Markdown structure.
            label = json.dumps(task["title"], ensure_ascii=False)
            ident = json.dumps(task["id"], ensure_ascii=False)
            detail = "; ".join(row["reasons"]) if queue == "decision" else task.get("next_action", "").strip() or "Next action missing"
            source = result.get("sources", {}).get(task["id"])
            trace = f"; source: {json.dumps(source['file'], ensure_ascii=False)} line {source['line']}" if source else ""
            lines.append(f"- {ident}: {label}; detail: " + json.dumps(detail, ensure_ascii=False) + trace)
    return safe_text("\n".join(lines)) + "\n"
