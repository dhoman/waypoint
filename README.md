# Waypoint

Discover a UI workflow with an LLM, save it as a typed capability graph, and
replay it with different inputs without a model. Artifacts hold website-specific
knowledge. Automation uses a local Playwright browser; desktop/native support is
not implemented.

## Start here

- Run it with the setup and commands below.
- Understand execution with the [architecture walkthrough](docs/ARCHITECTURE.md).
- Find files and classes in the [package map](waypoint/README.md).
- Add a surface or provider with the [extension guide](docs/EXTENDING.md).
- Change code with the [contributor guide](CONTRIBUTING.md), [test map](tests/README.md),
  and [agent instructions](AGENTS.md).
- Review the take-home in [REPORT.md](REPORT.md), [recorded evidence](evidence/README.md),
  and the [documentation index](docs/README.md).

The engine supports only artifact schema 2.0. Version-1 code, `--member` mode
and the fixture-specific `amend` command were removed; their evidence is
historical. The current CLI cannot run schema-1 artifacts. The `discover`,
`replay`, `inspect`, `qualify`, `fixture` and strict entrypoints remain. See the
package map for moved Python imports.

## Setup

Use the existing [uv](https://docs.astral.sh/uv/) installation.
`.python-version` selects Python 3.12; `uv.lock` pins dependencies.

```sh
uv sync --extra discovery --extra dev
uv run --no-sync playwright install chromium
```

Linux may require `uv run --no-sync playwright install --with-deps chromium`.
Headless runs need no display; manual control needs a desktop and `--headed`. A
remote desktop can provide a display; hosted infrastructure is optional.

Discovery requires `OPENAI_API_KEY` and a model selected via `--model` or
`WAYPOINT_MODEL`. The retained real runs used `gpt-5.4-mini`. Credentials are
read from the environment and never saved in artifacts. Only discovery calls the
model. Replay-only installation is `uv sync`; the provider SDK is optional. Use
`--no-sync` after selecting extras so subsequent commands keep that environment.

## Quick model-free demo

In terminal 1, start the synthetic member console with its legacy iframe:

```sh
uv run --no-sync waypoint fixture --port 8770
```

In terminal 2, replay the saved schema-2 artifact for another member:

```sh
uv run --no-sync python -m waypoint.strict replay \
  --artifact evidence/web-member-discovery-6/capability.json \
  --input memberId=M-202 --headed --out runs/member-replay

uv run --no-sync waypoint inspect \
  --artifact evidence/web-member-discovery-6/capability.json \
  --runs runs/member-replay --out runs/member-inspector.html
```

Expected result: M-202's two displayed invoices, amounts 84.25 and 15.75, total
100.00. Open `runs/member-inspector.html` in a browser. No server or frontend
build is needed for the inspector. Each `--out` must be a new directory.

Strict mode removes model credentials and verifies that provider imports and
non-loopback Python connections are blocked. Chromium's website traffic has a
separate runtime policy. Strict mode is not an OS sandbox. Each strict run saves
`isolation.json`.

## Discover on a website, then replay

Use public/synthetic data on a site you are authorized to automate:

```sh
uv run --no-sync waypoint discover \
  --url https://books.toscrape.com/ \
  --goal 'Open the category named by category and return the first three book titles and prices displayed in that category.' \
  --input category=Travel --model gpt-5.4-mini --headed \
  --out runs/books-discovery

uv run --no-sync python -m waypoint.strict replay \
  --artifact runs/books-discovery/capability.json \
  --input category=Poetry --headed --out runs/books-replay

uv run --no-sync waypoint inspect \
  --artifact runs/books-discovery/capability.json \
  --runs runs/books-replay --out runs/books-inspector.html
```

For your site, change the URL, goal and `--input NAME=VALUE` arguments. Inputs
are scalar strings, JSON numbers or booleans; replay requires the same
names/types, not the demonstrated values. Discover a separate capability for
each task/site. You do not write selectors, screens or extraction code first.

Inspect the draft and test new inputs for incorrect or overfitted model rules.
Rejected pre-action proposals get bounded discovery feedback; replay never calls
a model or repairs its graph. One route does not prove all business branches.
Tests cover an explicitly authored missing-member branch; discovery cannot infer
it from a successful search.

`result.json` contains outputs and failures; `events.jsonl` contains events. To
annotate a fully covered draft without modifying it:

```sh
uv run --no-sync waypoint qualify \
  --artifact runs/books-discovery/capability.json \
  --runs runs/books-replay --out runs/books-validated.json
```

Qualification requires matching artifact fingerprints and execution evidence for
every transition, alternative destination and terminal; it is not approval to
operate on arbitrary tenants or production systems.

## Same-session human control

For the local demo, inject a blocking notice:

```sh
uv run --no-sync python -m waypoint.strict replay \
  --artifact evidence/web-member-discovery-6/capability.json \
  --input memberId=M-202 \
  --url 'http://127.0.0.1:8770/?scenario=dialog' \
  --headed --interactive --out runs/handoff
```

At the pause, enter `take TOKEN` using the printed token. Dismiss the notice in
the same browser window, then enter `resume TOKEN`. You can also `cancel`.
Automation cannot act during human ownership. Resume observes again and verifies
a permitted checkpoint and identity; approval does not waive those checks.
Browser-page click targets and redacted input events are captured, not global
keystrokes or browser-chrome activity.

Other runtime options:

| Option | Effect |
|---|---|
| `--headed --prepare` | Manually prepare/login to the same fresh session, then press Enter. Storage is not persisted. |
| `--allow-origin https://login.example.com` | Authorize another frame/navigation/request origin. Popups remain blocked. |
| `--allow-method POST` | Permit that method across allowed origins, e.g. for a trusted login. Broad permission; use cautiously. |
| `--allow-control 'Exact label'` | Explicitly authorize an otherwise disallowed control. This may permit consequential actions. |

The fixture also supports `?scenario=slow`, `mismatch`, `ambiguous`, and
`readonly`. Developers configure these scenarios; the model cannot select them.
Do not assume a fixture variant is an approved graph branch.

## Development and limitations

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check waypoint tests
uv run --no-sync ruff format --check waypoint tests
```

The [test map](tests/README.md) explains focused runs, test-only adapters and
safety coverage. The browser adapter and in-memory test adapter exercise the
same surface interface. The in-memory adapter does not provide desktop support.

DOM forms, links, tables, repeated lists and named iframes are supported.
CAPTCHA, canvas-only controls, unnamed frames, popup authentication and complex
shadow-DOM workflows may require manual steps or adapter improvements.
Capabilities remain bounded, app-scoped drafts until validated; no global route
planner exists.

UI text is sent to the configured model during discovery and retained in local
evidence. Form masking and redacted input events do not provide production PII
removal. Use public/synthetic data only. Policy constrains origins, methods and
control semantics, but cannot prove that arbitrary page scripts or GET handlers
are harmless.

The adapter was implemented independently after an [OpenAdapt
investigation](docs/adr-001-surface.md); no OpenAdapt code was copied. The
assignment PDF was absent. No public repository push, deployment or submission
has been performed.
