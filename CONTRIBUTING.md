# Contributing

Read [AGENTS.md](AGENTS.md), the [architecture](docs/ARCHITECTURE.md) and the
[package map](waypoint/README.md). There is one current engine; do not start from
historical schema-1 evidence or the deleted flat modules.

## Environment and checks

```sh
uv sync --extra discovery --extra dev
uv run --no-sync playwright install chromium
uv run --no-sync pytest -q
uv run --no-sync ruff check waypoint tests
uv run --no-sync ruff format --check waypoint tests
```

Tests need Chromium and loopback socket access; they need no model credentials,
public internet, hosted browsers or desktop display. On Linux, Playwright system
dependencies may require `playwright install --with-deps chromium`. Headed manual
acceptance is separate from automated tests. See the [test map](tests/README.md)
for targeted commands and fixture ownership.

## Change workflow

1. Inspect existing work and preserve unrelated changes. Identify the owning
   package using the file map before adding files.
2. For changed behavior, write one failing test at the public interface. Implement
   enough to pass, then refactor. For structural changes, establish a passing
   baseline and preserve the observable outcomes through each move.
3. Test safety at the action seam: identity, ambiguity, policy, ownership and
   uncertain delivery must fail before incorrect follow-on actions.
4. Run focused tests while iterating, then the complete suite and formatting/lint.
5. Update the relevant docs when paths, interfaces, configuration or limitations
   change. Root README owns commands; package README owns file inventory;
   architecture and extension docs own relationships/invariants.
6. Commit coherent milestones with meaningful messages. Do not deploy, push,
   email a submission or run expensive external acceptance without authorization.

Do not add test-only selectors to production/demo UI to make discovery trivial.
Fixture setup may inject failures, but the model/runner must learn them through
the visible surface. In-memory adapters and scripted providers belong only in
`tests/support/` or test functions, never in claimed real-run evidence.

## Interface and dependency rules

- Use composition: `Replay` receives a `Surface`; discovery also receives a
  `Provider`. Adapters encapsulate their SDKs. No raw locator/handle crosses out.
- `domain/` is pure validated data. Runtime cannot import model/discovery modules,
  concrete surfaces, CLI wiring or demo state.
- `app/workflow.py` constructs concrete dependencies. Optional provider imports
  remain inside the discovery branch; CLI help/inspection do not load them.
- Keep new application knowledge in artifacts. Add a new surface under
  `surfaces/<name>/`, with explicit vocabulary changes if browser tags do not fit.
- Keep evidence redaction at capture/persistence seams. Never commit real tokens,
  browser storage, credentials or sensitive UI data.
- Do not weaken guards to make tests pass, silently merge ambiguous screens, add
  arbitrary-expression execution, or introduce replay-time model recovery.

`tests/app/test_dependencies.py` checks the dependency direction and lightweight
CLI loading. Runtime/discovery substitution tests exercise a non-Playwright
adapter. These protect the actual extension seam, not just directory naming.

## Artifacts, evidence and packaging

Schema-2 artifact serialization is checked against retained canonical hashes.
Internal imports may move, but an unchanged artifact must still mean the same
thing and match its evidence. Schema-1 support was deliberately removed; old
files/static inspectors are historical records. Never rewrite old evidence to
pretend it ran a new commit.

Use fresh `runs/...` directories for local experiments. Discovery evidence must
identify whether the provider was real or test-only. Existing evidence proves
specific executions, not universal website reliability. Qualification annotates
coverage, not permission to operate on a new scope.

When moving package resources, build and inspect a wheel:

```sh
uv build --wheel
```

The wheel must contain `waypoint/surfaces/browser/observe.js` and
`waypoint/inspector/template.html`. Test importing/running from an installed wheel
outside this checkout, not only an editable install. Keep these resources next to
their implementation; there is no frontend build step or external asset CDN.
