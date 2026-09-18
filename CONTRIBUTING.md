# Contributing

Read [AGENTS.md](AGENTS.md), the [architecture](docs/ARCHITECTURE.md) and the
[package map](waypoint/README.md). Use the current engine, not historical
schema-1 evidence or deleted flat modules.

## Environment and checks

```sh
uv sync --extra discovery --extra dev
uv run --no-sync playwright install chromium
uv run --no-sync pytest -q
uv run --no-sync ruff check waypoint tests
uv run --no-sync ruff format --check waypoint tests
```

Tests require Chromium and loopback socket access, but no model credentials,
public internet, hosted browsers or desktop display. On Linux, Playwright system
dependencies may require `playwright install --with-deps chromium`. Headed
manual acceptance is separate from automated tests. See the [test
map](tests/README.md) for targeted commands and fixture ownership.

## Change workflow

1. Preserve unrelated changes. Use the package map to identify where new files belong.
2. For changed behavior, write one failing test at the public interface. Implement
   enough to pass, then refactor. For structural changes, start from passing
   tests and preserve behavior through each move.
3. Test safety at action delivery. Identity, ambiguity, policy, ownership and
   uncertain-delivery checks must prevent incorrect follow-on actions.
4. Run focused tests while iterating, then the complete suite and formatting/lint.
5. Update the relevant docs when paths, interfaces, configuration or limitations
   change. The root README covers commands; the package README lists files;
   architecture and extension docs explain relationships and invariants.
6. Commit coherent milestones with meaningful messages. Do not deploy, push,
   email a submission or run expensive external acceptance without authorization.

Do not add test-only selectors to production/demo UI to simplify discovery.
Fixture setup may inject failures, but the model/runner must detect them through
the visible UI. In-memory adapters and scripted providers belong only in
`tests/support/` or test functions, never in claimed real-run evidence.

## Interface and dependency rules

- Use composition. `Replay` receives a `Surface`; discovery also receives a
  `Provider`. Keep SDK objects, including raw locators/handles, inside adapters.
- `domain/` is pure validated data. Runtime cannot import model/discovery modules,
  concrete surfaces, CLI wiring or demo state.
- `app/workflow.py` constructs concrete dependencies. Optional provider imports
  remain inside the discovery branch; CLI help/inspection do not load them.
- Keep new application knowledge in artifacts. Add a new surface under
  `surfaces/<name>/`, with explicit vocabulary changes if browser tags do not fit.
- Redact evidence at capture and persistence. Never commit real tokens,
  browser storage, credentials or sensitive UI data.
- Do not weaken guards to make tests pass, silently merge ambiguous screens, add
  arbitrary-expression execution, or introduce replay-time model recovery.

`tests/app/test_dependencies.py` checks the dependency direction and lightweight
CLI loading. Runtime/discovery substitution tests exercise a non-Playwright
adapter to verify that engines accept another implementation.

## Artifacts, evidence and packaging

Tests check schema-2 serialization against retained canonical hashes. Moving
imports must preserve artifact meaning and evidence compatibility. Schema-1
support was removed; old files/static inspectors are historical records. Never
rewrite evidence to imply it ran a newer commit.

Use fresh `runs/...` directories for local experiments. Discovery evidence must
identify whether the provider was real or test-only. Existing evidence proves
specific executions, not universal website reliability. Qualification records
coverage and grants no permission to operate on a new scope.

When moving package resources, build and inspect a wheel:

```sh
uv build --wheel
```

The wheel must contain `waypoint/surfaces/browser/observe.js` and
`waypoint/inspector/template.html`. Test importing/running from an installed
wheel outside this checkout, not only an editable install. Keep these resources
next to their implementation; there is no frontend build step or external asset
CDN.
