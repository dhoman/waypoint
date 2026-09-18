# Retained execution evidence

All run directories here contain **actual local browser executions with fake
application data**. There are no fabricated provider traces in this directory.
Authored routes and synthetic providers exist only in `tests/` and temporary
pytest output. One example of each exception is not a reliability estimate.

Open [inspector.html](inspector.html) locally; it embeds the artifact, events,
outcomes, filtered snapshots and screenshots. Select `identity-mismatch` for a
hard stop or `handoff` for the manual intervention history.

## Inventory

| Directory/file | Evidence |
|---|---|
| `discovery-a/` | Initial genuine OpenAI run, 4 chosen UI actions + finish; member A, total 165.50; draft revision 1 |
| `capability.json` | Revision 2: original observed route plus explicitly authored missing-member outcome |
| `capability-validated.json` | Same executable revision with validation annotations from B and missing-member runs; original file untouched |
| `replay-b/` | Strict replay for member B; two invoices, total 100.00 |
| `missing-member/` | M-999 returns `business_outcome / member_not_found` |
| `slow-load/` | Successful replay through a 1.2s visible transient; readiness bounded by 5s |
| `identity-mismatch/` | Requested M-202 but observed M-101; stops at t2 before invoices, with screenshot and snapshot |
| `ambiguous-target/` | Duplicate matching member rows; stops before profile selection, with screenshot and snapshot |
| `handoff/` | Same headed context/page pauses at t2; manual dismiss click, fresh identity/checkpoint validation, then success |
| `discovery-verified/` | Second genuine model run against committed source, including exact source fingerprint |
| `replay-verified/` | Final B replay against that same source; saved active import/network isolation proof |

Each run has `events.jsonl` and `result.json`; discovery runs additionally have
their saved capability and final UI evidence. Failure PNGs mask form controls.
Displayed names and IDs are intentionally synthetic. Provider prompts, API keys,
raw conversations, browser storage, and typed operator values are absent.

The retained handoff has a manual `Dismiss notice` click (event 22), followed by
`resume_validated` at checkpoint s3 and B's outputs. The operator did not enter a
note in this retained run. Redacted input-event behavior is implemented and
covered by `test_manual_input_evidence_cannot_retain_typed_values`. Tests also
verify that automation cannot act during human ownership and that an unresolved
dialog cannot resume. No automation dismissed the notice in the retained run.

## Exact environment and code references

- Host: macOS 26.2, arm64; Python 3.12.13 managed by the preinstalled uv.
- Project 0.1.0; dependencies in `uv.lock` (Playwright 1.63.0 / Chromium build
  1243, Pydantic 2.13.5, OpenAI SDK 2.54.0).
- Discovery provider: OpenAI Responses, configured model `gpt-5.4-mini`,
  `store=False`; credential obtained from `OPENAI_API_KEY`, never persisted.
- The final verified pair ran code commit `716d5c5`. Their source SHA-256 is
  `61d1394948798ddc66f65c9321c029b9642b1c1c496823c047860765b6c1b5f2`.
  It hashes the sorted filenames and bytes of `waypoint/*.py` and `*.html`.
  Later inspector-only label fixes do not change replay/discovery behavior.
- Replay artifact digest (canonical Pydantic JSON):
  `1dae1a9c998eb02d959b873b904c07a4df55b58c1b2997782709bd1b48008aad`.
- Initial discovery predates the source-fingerprint field (implementation milestone
  `99a9981`); initial replay/handoff similarly predate that field (milestone
  `0c879f3`). These are milestones, **not exact byte fingerprints** of those early
  in-progress executions. The final verified pair supplies exact provenance.
- Intermediate exception runs carry their own source digest in `run_started`.
  Evidence references containing a run ID are logical references: find the
  directory whose `run_started.run_id` equals that ID; they are not file paths.

## Commands actually used

Fixture remained at `http://127.0.0.1:8765/`:

```sh
.venv/bin/python -m waypoint.cli fixture
.venv/bin/python -m waypoint.cli discover --model gpt-5.4-mini --member M-101 --out evidence/discovery-a
.venv/bin/python -m waypoint.cli amend --artifact evidence/discovery-a/capability.json --out evidence/capability.json
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --out evidence/replay-b
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-999 --out evidence/missing-member
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --url 'http://127.0.0.1:8765/?scenario=slow' --out evidence/slow-load
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --url 'http://127.0.0.1:8765/?scenario=mismatch' --out evidence/identity-mismatch
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --url 'http://127.0.0.1:8765/?scenario=ambiguous' --out evidence/ambiguous-target
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --url 'http://127.0.0.1:8765/?scenario=dialog' --headed --interactive --out evidence/handoff
# Entered take TOKEN, operator clicked Dismiss notice, entered resume TOKEN.
.venv/bin/python -m waypoint.cli qualify --artifact evidence/capability.json --runs evidence/replay-b evidence/missing-member --out evidence/capability-validated.json
.venv/bin/python -m waypoint.cli discover --model gpt-5.4-mini --member M-101 --out evidence/discovery-verified
.venv/bin/python -m waypoint.strict replay --artifact evidence/capability.json --member M-202 --out evidence/replay-verified
.venv/bin/pytest -q
.venv/bin/ruff check waypoint tests
.venv/bin/ruff format --check waypoint tests
```

Use fresh `runs/...` output directories to reproduce; evidence is intentionally
not overwritten by discovery/replay. `isolation.json` is present in later strict
runs. Earlier strict runs printed the same active denial proof to stdout but
did not yet save that separate file; `replay-verified` closes that evidence gap.

Final acceptance: 27 focused tests pass; Ruff and formatting pass. Policy refusal
and uncertain-write refusal are test scenarios, not claimed model discoveries.
The graph inspector was exercised in Chromium and its screenshot visually
reviewed. No desktop/native adapter or Linux desktop session was tested. The PDF
brief was absent. No public push, deployment, or submission was performed.
