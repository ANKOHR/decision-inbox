# Local build evidence

Measured 1 October 2026 using Python 3.12.10 on Windows, CPU-only standard-library application. All task records in this benchmark were labelled synthetic. No real-use accuracy or savings were measured.

Reproduce with `python -m pytest -q` and `python scripts/verify_demo.py` after offline local installation. The verifier executes the installed `di` executable, not a mocked parser. It uses a temporary directory and runs fixtures, run, and Markdown report as separate processes, then verifies JSON report output separately.

| Measurement | Observed result |
| --- | --- |
| Synthetic records | 200 |
| Decision records | 120 |
| Execution records | 80 |
| Action-ready execution records | 80 |
| Execution records needing next action | 0 |
| False positive decisions against planted truth | 0 |
| Missed planted decisions | 0 |
| Installed CLI end-to-end elapsed time | 0.681210 seconds |
| Separate JSON report elapsed time including process startup | 0.209495 seconds |
| Real-world classification accuracy | Unmeasured |
| Time saved against a human baseline | Unmeasured |
| Money saved | Unmeasured |

Counts reconcile: 120 + 80 = 200; 200 synthetic + 0 user-declared real = 200. The independent expectation file has literal counts and enumerated queue IDs. All queue IDs match exactly. Timings are observations from this machine and vary on rerun; they are not deterministic application outputs or promises for other hardware.

The test suite verifies exact counts and IDs, empty input, field/file/line diagnostics, duplicates, negative and extreme values, future creation dates against explicit reference dates, long Unicode text, Windows paths, byte-identical snapshots and Markdown reports, provenance on every output surface, no forbidden punctuation, stale-state preservation after failed input, tampered snapshot rejection, and atomic output failure cleanup.

A mutation test clears a planted decision signal in the fixture and observes 119 decisions and 81 executions in the CLI report. A separate test corrupts only the expectation file and observes unchanged computed results. These distinguish actual computation from hardcoded fixture answers.

Evidence-based build improvement: adversarial punctuation tests exposed an escaping regression. Fixing the renderer made both output restrictions and lossless JSON round-trip pass. The two-week real-use improvement hook remains pending and is specified in README.md and TRIAL-TEMPLATE.md.

Acceptance verdict for this local build: synthetic acceptance criteria met. Product verdict: pending the two-week real-use evidence window; no expand, integrate, commercialise, maintain or kill claim has been invented.
