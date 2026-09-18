# Waypoint

Discover one UI capability with an LLM, compile its observed route, then replay
with different inputs **without model access**. This take-home uses a synthetic
legacy member console, a real iframe, ordinary forms/tables, and fake data.

The saved LLM run navigated member M-101's invoices ($165.50). Strict replay read
M-202's different invoices ($100.00). A headed run paused for an unexpected
dialog, captured the operator's dismiss click, validated the same live page,
and completed. [Open the saved inspector](evidence/inspector.html) in a browser;
select the identity-mismatch or handoff overlay and click an edge.

## Setup

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and local Chromium.
The existing uv-managed Python 3.12.13 was used here; no second version manager
is required. `.python-version` selects Python and `uv.lock` pins dependencies.

```sh
uv sync --extra discovery --extra dev
uv run --no-sync playwright install chromium
```

On Linux, install Playwright's OS dependencies if needed:
`uv run --no-sync playwright install --with-deps chromium`.
Headless replay needs no display. Manual takeover needs a local desktop and
`--headed`; an optional remote desktop can provide that display in CI. A bare
Xvfb instance alone does not provide a human an interactive screen.

Discovery alone requires `OPENAI_API_KEY` in the environment and a selected
model (`--model` or `WAYPOINT_MODEL`). Do not paste credentials into artifacts.
The recorded run used `gpt-5.4-mini`, checked against the current
[model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
and the actual API. The provider uses
[Responses structured output](https://developers.openai.com/api/docs/guides/structured-outputs),
`store=False`, and no provider retry. There is no hardcoded runtime model default.

## One path from discovery to inspection

Start the application in terminal 1:

```sh
uv run --no-sync waypoint fixture
```

In terminal 2 (each `--out` must be a fresh directory):

```sh
# The only step below that calls a model. Uses the existing OPENAI_API_KEY.
uv run --no-sync waypoint discover --model gpt-5.4-mini \
  --member M-101 --out runs/discovery

# Add the explicitly authored missing-member outcome as a new draft revision.
uv run --no-sync waypoint amend \
  --artifact runs/discovery/capability.json --out runs/capability.json

# API credentials removed; provider imports and external Python sockets blocked.
uv run --no-sync python -m waypoint.strict replay \
  --artifact runs/capability.json --member M-202 --out runs/replay

uv run --no-sync python -m waypoint.strict replay \
  --artifact runs/capability.json --member M-999 --out runs/missing

uv run --no-sync waypoint qualify --artifact runs/capability.json \
  --runs runs/replay runs/missing --out runs/capability-validated.json

uv run --no-sync waypoint inspect --artifact runs/capability-validated.json \
  --runs runs/replay runs/missing --out runs/inspector.html
```

Open `runs/inspector.html` with any browser. It is a self-contained, offline HTML
file: no web service, CDN, graph editor, or build tool. The checked-in
`evidence/inspector.html` is ready to open. On macOS, `open evidence/inspector.html`.
The selected run shows actual completed edges, failures/interventions, identity
facts, recognition checks, actions, provenance, evidence and timing categories.

For the shortest model-free demo, start the fixture and run:

```sh
uv run --no-sync python -m waypoint.strict replay \
  --artifact evidence/capability.json --member M-202 --out runs/quick-replay
```

Replay-only installation is `uv sync` (without the `discovery` extra); the provider
SDK is optional. Use `--no-sync` after choosing extras so uv does not change the
environment for later commands. `python -m waypoint.strict --self-test` attempts
a prohibited provider import and external connection and verifies both fail.
Strict replay also writes `isolation.json`; this is stronger than counting calls,
but is not an OS sandbox for arbitrary hostile Python programs.

## Human takeover on the same session

```sh
uv run --no-sync python -m waypoint.strict replay \
  --artifact evidence/capability.json --member M-202 \
  --url 'http://127.0.0.1:8765/?scenario=dialog' \
  --headed --interactive --out runs/handoff
```

The browser remains open at the notice. In the command terminal:

1. Enter `take TOKEN`, using the fresh token printed for this intervention.
2. In that **same Chromium window**, optionally enter a fake operator note and
   click **Dismiss notice**. You may also manually reach the invoice checkpoint.
3. Enter `resume TOKEN`. Fresh recognition, entity identity, and outgoing guards
   must pass. If they do not, ownership stays human. `cancel` ends the run.

Automation cannot act while awaiting human control, during human ownership, or
during resume validation. Duplicate/stale commands fail. The CLI explicitly
transfers ownership; a browser click alone does not authorize replay. A paused
result is `awaiting_intervention`, never success. Noninteractive runs save that
result and close; they cannot later resume a destroyed session.

Captured in-page clicks include target labels; input events contain `[redacted]`,
never typed values. Browser chrome and OS interactions are not recorded. DOM
`isTrusted` is not proof of physical human input; tests and tools can produce
trusted events. The retained human demonstration contains the actual dismiss
click; input-value redaction has a focused test. The capture is session-scoped,
not a global keyboard logger.

## Reproducible scenarios and tests

With the fixture running, use the same artifact and member M-202, changing only
the runtime URL and output directory:

| Scenario | Runtime URL suffix | Expected result |
|---|---|---|
| Different member | `/` | `succeeded`, B's two invoices, total 100 |
| Missing member | `/`, pass `--member M-999` | `business_outcome / member_not_found` |
| Slow load | `/?scenario=slow` | B's outputs after a bounded readiness wait |
| Blocking notice | `/?scenario=dialog` | `awaiting_intervention`; headed interactive handoff |
| Wrong record | `/?scenario=mismatch` | `failed / identity`, before opening invoices |
| Duplicate results | `/?scenario=ambiguous` | `failed / ambiguity`, before selecting a profile |
| Read-only variant | `/?scenario=readonly` | intervention; unsupported variant is not bypassed |

These are developer fixture controls. Neither discovery nor replay calls fixture
setup APIs or reads fixture code/data; they observe the resulting UI. The model
is not given these scenario switches.

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check waypoint tests
uv run --no-sync ruff format --check waypoint tests
```

Tests prioritize public behavior: actual browser output, wrong-entity refusal,
ambiguous screens/targets/guards, malformed graphs, policy-disallowed clicks,
loading deadlines, no-progress discovery, ownership and stale resume, redacted
input events, uncertain-write retry refusal, and inspector interaction. Test
provider responses and authored routes live in `tests/`; they are not real
discovery evidence. TDD was used incrementally after the initial schema scaffold.

## Code map and limits

| Module | Responsibility |
|---|---|
| `schema.py` | Versioned artifact, typed predicates/actions, graph validation |
| `surface.py`, `browser.py`, `policy.py` | Async session, structural resolution, allowlist and evidence |
| `discovery.py`, `provider.py`, `compiler.py` | Constrained LLM loop and deterministic route compilation |
| `recognition.py`, `engine.py`, `delivery.py` | Model-free interpretation, checks, outcomes and uncertainty |
| `ownership.py`, `evidence.py` | Transfer protocol, correlated trace and capture boundary |
| `inspector.py`, `inspector.html` | Local read-only graph/run inspection |
| `qualification.py` | Evidence annotations with artifact-digest and coverage checks |
| `fixture.py` | Developer-owned synthetic application; not an agent tool |

This is one bounded browser capability, not a general route planner. Logical
screen types are reused; identity is separately bound to mandatory `memberId`.
Action retries are disabled (only `retries: 0` is admitted); modeled recovery is
a bounded wait for visible loading. No generic Back/reset or model self-healing.
The main flow is read-only. A synthetic unit test covers uncertain-write refusal;
there is no financial transaction implementation.

The allowlist admits only the configured loopback origin, fixed app routes, GET
requests, a specific search field/form, and qualified navigation controls.
Redirect requests, frames and popups are checked/blocked. It does not prove that
arbitrary JavaScript or GET handlers on a malicious allowed app are harmless.
Only the trusted synthetic-local app profile is supported. Screenshots mask form
values; visible fixture identities remain fake and are intentionally inspectable.
This is **not production PII redaction**, tenant isolation, or a security sandbox.

[REPORT.md](REPORT.md) describes the design and cuts.
[ADR 001](docs/adr-001-surface.md) records the bounded OpenAdapt investigation and
direct-adapter choice; no OpenAdapt code was copied. Native/desktop portability
is an unimplemented seam, not a working adapter. Validation annotations are
saved separately; they never rewrite an active artifact. Evidence counts are
tiny demonstrations, not a reliability estimate.

The assignment PDF was not present. This implementation follows the requirements
reproduced in the build prompt. Nothing was pushed, deployed, or emailed.
