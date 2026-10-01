# Decision Inbox

Decision Inbox is a local Python CLI that separates tasks requiring an explicit decision from routine execution. It helps Henry keep school, outreach, builds, and applications in separate decision and execution queues. It uses declared facts, not language models or guessed intent.

Hypothesis: explicit deterministic rules can make this separation trustworthy when outputs are tested against planted ground truth. Acceptance: the labelled 200-record fixture must yield exactly 120 decisions and 80 executions, with zero false positives and zero missed planted decisions. The complete demo and report must run in under five seconds locally.

## Quickstart

Python 3.10+ and setuptools 68+ are required. Runtime uses only the standard library. Installation can be completed offline with already installed build tools:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-deps --no-build-isolation -e .
di fixtures --out demo
di run --input demo
di report --format md
```

The virtualenv reuses already installed build and test tools for offline setup. If virtualenv is unavailable, the same install works with the current Python. If the user Scripts directory is absent from PATH, use `python -m decision_inbox.cli` in place of `di`. The fixture generator refuses to overwrite existing fixture files. Choose a new directory for a fresh demo.

For the smallest version, run `di run --input demo/tiny`, then `di report --format md`. This uses five hand-written realistic synthetic records and computes three decisions and two executions.

Run tests with `python -m pytest -q` (pytest must already be installed for an offline setup). Run `python scripts/verify_demo.py` to reproduce the installed-CLI benchmark. See [EVIDENCE.md](EVIDENCE.md) for measured local acceptance results and [BUILD-DONE.txt](BUILD-DONE.txt) for the build checkpoint. No network calls, GPU dependencies, databases, or model calls exist in the application.

## Input format

Put one or more UTF-8 `.jsonl` files directly inside an input directory. One JSON object per line. Blank lines and lines starting with `#` are allowed. JSONL is the supported task format; CSV, YAML and standalone JSON task files produce a named format error, rather than silently disappearing. Only generated `expectations.json` and `README.md` are ignored. Subdirectories are not scanned, so `demo/tiny` does not add five records to the 200-record demo.

This is an illustrative schema example, not Henry's real data:

```json
{"id":"example-1","title":"Choose an application priority","synthetic":true,"decision_required":true,"decision_reason":"Pick the application to work on first","alternatives":["Application A","Application B"],"missing_information":[],"next_action":"","effort_minutes":20,"created_on":"2026-09-30","reference_date":"2026-09-30"}
```

For Henry's own tasks entered by hand, use `synthetic: false`. That flag declares provenance; the tool cannot independently verify it. Do not mark copied examples as real. Real trial data and results remain local and must not be committed.

| Field | Rule |
| --- | --- |
| `id` | Required nonblank string, unique across all input files |
| `title` | Required nonblank string |
| `synthetic` | Required actual JSON boolean, never inferred |
| `decision_required` | Required actual JSON boolean |
| `decision_reason` | Required nonblank text if `decision_required` is true |
| `alternatives` | Optional list of distinct nonblank strings; two or more triggers a decision |
| `missing_information` | Optional list of distinct nonblank strings; any entries trigger a decision |
| `next_action` | Optional text; execution tasks without it are explicitly counted as needing a next action |
| `effort_minutes` | Optional integer from 0 to 1,000,000; user supplied and unmeasured, never used as time saved |
| `created_on`, `reference_date` | Optional pair of strict ISO YYYY-MM-DD dates; creation must not be after the explicit reference date |

All text fields are limited to 10,000 characters. Lists have at most 100 items, each at most 10,000 characters. Unknown fields, negative effort, booleans pretending to be numbers, duplicate JSON keys, duplicate IDs, invalid dates, and future creation dates relative to the supplied reference date are rejected. `amount` is not a supported field. There is no wall-clock date validation: the same explicit dates always give the same result. Input paths and Unicode strings are supported. User-supplied forbidden punctuation is escaped as a Unicode escape in outputs; JSON round-trips the original value.

A decision is triggered by any of: `decision_required: true`, two or more explicit alternatives, or nonempty missing information. All triggered reasons are retained. Otherwise a task belongs to execution. `action_ready` means only that a next action is supplied for an execution task, not that resources or permission have been verified. A single alternative alone is not a choice and does not trigger a decision. The CLI does not inspect titles for meaning or claim that declared classifications match human judgement.

## Subcommands

```powershell
di fixtures --out demo                 # Labelled synthetic fixture set
di run --input demo                    # Validate, compute, save local snapshot
di report --format md                  # Full report and provenance banner
di report --format json --out report.json
di triage --queue decision             # Decision records and reasons
di triage --queue execution            # Execution records and readiness
di next --id task-121                  # Inspect one task, no task mutation
```

Every subcommand has `--help` and an example. `run`, `report`, `triage`, and `next` accept `--state <path>`; default is `.decision-inbox/result.json`. `report` accepts `--out <path>` and writes atomically. Without `--out`, reports go to standard output. `run` outputs computed JSON and provenance, not an estimated success message. Domain inspection commands also carry provenance and the honesty statement.

Reports read the last successful snapshot. Rerun `run` after editing input files. Snapshots contain every task, explicit reasons, per-record file and line provenance, and reconciled counts. Report loading recomputes counts and classification and rejects inconsistent snapshots. This detects accidental corruption, not malicious forgery; source declarations are trusted. Files in the state directory are local and gitignored by default.

## Architecture

```text
UTF-8 JSONL files
    -> cli.load_tasks (parse, validate, file/line provenance)
    -> core.compute (pure schema checks, classify, sort, reconcile)
    -> atomic local result.json snapshot
    -> report.render (Markdown or JSON, provenance, explicit reasons)
    -> stdout or atomic output file

fixtures.fixture_files -> labelled inputs + independent expectations
pytest -> core, parser, snapshots, reports, adversarial cases
```

Stable ID ordering, sorted file enumeration, sorted JSON keys, LF output and no run timestamps give byte-identical snapshots and reports for unchanged inputs. No randomness is used, so there is no seed. Determinism applies to computed artifacts; measured benchmark timings naturally vary. The engine never reads the expectations file.

## Honesty boundary

Counts are computed exactly from explicit inputs. Classification is rule agreement with those inputs, not discovery of what truly requires thought. Synthetic fixture agreement is measured against planted truth; it is not measured real-world accuracy. No measured time saved, money saved, productivity gain, or predicted outcome is claimed. Such figures are unmeasured and are not reported. Optional effort is a user-supplied unmeasured estimate, never aggregated as savings. Runtime benchmarks measure elapsed execution only, not time saved against a human baseline.

Every fixture JSONL begins with a SYNTHETIC header comment and every record carries `synthetic: true`. Expectations are valid JSON with a synthetic field and a synthetic label; JSON cannot contain header comments. Fixture Markdown begins with a synthetic HTML comment. Every report shows synthetic and user-declared real counts, source file names, and task-level traceability. Even empty input renders a provenance banner and zero counts. Mixed provenance is supported. No real-use trial has yet been performed.

## Failure modes

- Malformed JSONL: `ParseError` names the file, line and JSON column. Invalid UTF-8 names the file and the affected line.
- Missing input: `MissingInputError` includes a fixture command hint and exits 2.
- Schema drift: `SchemaError` names the file, line and offending field or ID. Unsupported formats are named errors.
- Missing snapshot or corrupted snapshot: `MissingResultError` or `ResultError` with a rerun hint or explanation.
- Output write failure: `WriteError`, exit 2, no partial output file or temporary file left behind. Existing output remains intact if replacement fails. Fixture files are individually atomic; a later failure can leave earlier completed fixture files.
- Failed input validation never replaces the previous successful snapshot. That snapshot remains old until a successful rerun.
- Failure to declare decisions correctly produces incorrect real-world classification. The tool cannot detect unexpressed uncertainty or interpret prose.

## Evidence-based improvement hook and verdict

Start a two-week evidence window on the first real-use day. Record the start date locally, each day used, and a hand-checked sample of the two queues. The primary metric is classification error rate: `(false decisions + missed decisions) / hand-checked tasks`. Record the sample IDs, human labels and disagreement reasons. Do not substitute synthetic accuracy for this metric. No samples means accuracy is unmeasured.

At day 14, if the error rate exceeds 10 percent, fix the top documented failure cause and rerun the sample, or kill the project with the reason. If there was no actual use, kill it. If time saved is later measured, record a timed manual baseline on the same tasks, CLI plus review time, sample size and method; otherwise it remains unmeasured.

The final verdict is pending the real-use window. Record it locally using [TRIAL-TEMPLATE.md](TRIAL-TEMPLATE.md), with an explicit reason: expand if it earns daily use or revenue, integrate if it overlaps heavily with a sibling project, commercialise if a buyer would pay as-is, maintain as portfolio evidence otherwise, or kill if never used or unable to meet acceptance criteria. No future observation or completed two-week trial is invented by this build.

See [LESSONS.md](LESSONS.md) for validated assumptions and the operating rule for future builds. Publishing to `ANKOHR/decision-inbox` is handled by a separate verification step. This build is local only.
