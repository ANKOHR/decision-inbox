"""Local-only CLI. Each task file is parsed as UTF-8 JSONL with # comment support."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import InboxError, compute, validate_task
from .fixtures import fixture_files
from .report import banner, json_text, render, safe_text


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise InboxError(f"WriteError: {path}: {exc.strerror or str(exc)}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_tasks(directory, with_sources=False):
    directory = Path(directory)
    if not directory.is_dir():
        raise InboxError(f"MissingInputError: {directory}: expected an input directory; use di fixtures --out demo")
    tasks = []
    sources = {}
    seen = set()
    for path in sorted(directory.iterdir()):
        if path.is_dir() or path.name in ("expectations.json", "README.md"):
            continue
        if path.suffix.lower() != ".jsonl":
            raise InboxError(f"SchemaError: {path}: line 1: unsupported file format; use UTF-8 .jsonl")
        try:
            with path.open("rb") as stream:
                for line_number, raw_line in enumerate(stream, 1):
                    try:
                        line = raw_line.decode("utf-8-sig" if line_number == 1 else "utf-8")
                    except UnicodeError:
                        raise InboxError(f"ParseError: {path}: line {line_number}: invalid UTF-8 encoding") from None
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    try:
                        def pairs(items):
                            obj = {}
                            for key, value in items:
                                if key in obj:
                                    raise InboxError(f"SchemaError: duplicate field {key}")
                                obj[key] = value
                            return obj
                        task = json.loads(line, object_pairs_hook=pairs)
                        validate_task(task)
                        if task["id"] in seen:
                            raise InboxError(f"SchemaError: duplicate id {task['id']}")
                        seen.add(task["id"])
                        tasks.append(task)
                        sources[task["id"]] = {"file": path.name, "line": line_number, "synthetic": task["synthetic"]}
                    except json.JSONDecodeError as exc:
                        raise InboxError(f"ParseError: {path}: line {line_number}, column {exc.colno}: {exc.msg}") from None
                    except InboxError as exc:
                        raise InboxError(f"{str(exc).split(':', 1)[0]}: {path}: line {line_number}: {str(exc).split(':', 1)[1].strip()}") from None
        except UnicodeError:
            raise InboxError(f"ParseError: {path}: line 1: invalid UTF-8 encoding") from None
        except OSError as exc:
            raise InboxError(f"ReadError: {path}: line 1: {exc.strerror}") from None
    return (tasks, sources) if with_sources else tasks


def load_result(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value["schema_version"] != 1 or not isinstance(value["records"], list) or any(not isinstance(row, dict) for row in value["records"]):
            raise ValueError("unsupported result schema")
        checked = compute([row["task"] for row in value["records"]])
        sources = value.get("sources")
        if sources is not None:
            expected_ids = {row["task"]["id"] for row in checked["records"]}
            if not isinstance(sources, dict) or set(sources) != expected_ids:
                raise ValueError("sources must cover every task id")
            for row in checked["records"]:
                source = sources[row["task"]["id"]]
                if not isinstance(source, dict) or set(source) != {"file", "line", "synthetic"} or not isinstance(source["file"], str) or type(source["line"]) is not int or source["line"] < 1 or type(source["synthetic"]) is not bool or source["synthetic"] != row["task"]["synthetic"]:
                    raise ValueError("invalid provenance source")
            checked["sources"] = sources
        if checked != value:
            raise ValueError("stored results do not reconcile; run di run again")
        return checked
    except FileNotFoundError:
        raise InboxError(f"MissingResultError: {path}: run di run --input <dir> first") from None
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise InboxError(f"ResultError: {path}: {exc}") from None


def parser():
    root = argparse.ArgumentParser(description="Separate explicitly declared decisions from routine execution. Local files only.")
    commands = root.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures", help="Generate labelled synthetic fixtures", epilog="Example: di fixtures --out demo")
    fixtures.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Validate and classify every input record", epilog="Example: di run --input demo")
    run.add_argument("--input", required=True)
    report = commands.add_parser("report", help="Render computed results and provenance", epilog="Example: di report --format md --out report.md")
    report.add_argument("--format", choices=("md", "json"), default="md")
    report.add_argument("--out")
    triage = commands.add_parser("triage", help="Show a queue with explicit classification reasons", epilog="Example: di triage --queue decision")
    triage.add_argument("--queue", choices=("decision", "execution"), default="decision")
    next_cmd = commands.add_parser("next", help="Inspect one task's decision or execution requirements", epilog="Example: di next --id task-121")
    next_cmd.add_argument("--id", required=True)
    for command in (run, report, triage, next_cmd):
        command.add_argument("--state", default=".decision-inbox/result.json", help="Local computed result file (default: .decision-inbox/result.json)")
    return root


def main(argv=None):
    # Windows redirected streams can otherwise use a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            outputs = fixture_files()
            conflicts = [str(Path(args.out) / name) for name in outputs if (Path(args.out) / name).exists()]
            if conflicts:
                raise InboxError("WriteError: refusing to overwrite fixture files: " + ", ".join(conflicts))
            for name, content in outputs.items():
                atomic_write(Path(args.out) / name, content)
            print("Generated 200 SYNTHETIC records and a 5-record SYNTHETIC subset. No savings measured.")
        elif args.command == "run":
            tasks, sources = load_tasks(args.input, with_sources=True)
            result = compute(tasks)
            result["sources"] = sources
            atomic_write(args.state, json_text(result))
            print(render(result, "json"), end="")
        else:
            result = load_result(args.state)
            if args.command == "report":
                output = render(result, args.format)
                if args.out:
                    atomic_write(args.out, output)
                else:
                    print(output, end="")
            elif args.command == "triage":
                subset = [r for r in result["records"] if r["queue"] == args.queue]
                print(json_text({"provenance_banner": banner(result), "honesty": result["honesty"], "records": subset}), end="")
            else:
                matches = [r for r in result["records"] if r["task"]["id"] == args.id]
                if not matches:
                    raise InboxError(f"TaskNotFoundError: id {args.id}")
                print(json_text({"provenance_banner": banner(result), "honesty": result["honesty"], "record": matches[0]}), end="")
        return 0
    except InboxError as exc:
        print(safe_text(str(exc)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
