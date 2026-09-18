# Test map

The suite tests the single schema-2 engine. It does not require model credentials,
public internet or a desktop display; real browser tests use headless Chromium
and local synthetic servers. `tests/support/` is never a production adapter or
source of claimed LLM evidence.

| Area | Behaviors |
|---|---|
| `domain/` | Graph/input rejection; no demonstrated-input defaults; ambiguous transition guards; retained artifact fingerprints |
| `runtime/` | Different-input output correctness; business branches; identity/target failures; bounded loading; same-session handoff; ownership and uncertain-delivery refusal |
| `discovery/` | Entity predicates separate from screen types; rejected extraction rules; bounded no progress; model/surface substitution |
| `surfaces/` | Arbitrary forms and real iframe navigation; origin/method/control policy; consequential click refused before delivery |
| `evidence/` | Redacted manual inputs; matching artifact/coverage requirements for qualification |
| `inspector/` | Safe embedded UI text; failed-edge selection and rich evidence in a real browser |
| `app/` | Strict import/network isolation; no optional SDK/browser loading just to import CLI; dependency direction |

Support files:

- `support/catalog.py`: unrelated synthetic parts website for adapter tests.
- `support/memory_surface.py`: in-memory structural adapter with no browser,
  locator or URL; exercises discovery/replay through the `Surface` seam.
- `support/artifacts.py`: specializes a retained schema-2 member artifact for an
  ephemeral test origin and optionally adds an **authored test-only** missing-member
  branch. It does not claim that branch was discovered by an LLM.
- `waypoint/demo/member_console.py`: the real local fixture used by scenario tests.

## Running tests

From the repository root, after setup in the main README:

```sh
uv run --no-sync pytest -q
uv run --no-sync pytest -q tests/domain tests/app
uv run --no-sync pytest -q tests/surfaces
uv run --no-sync pytest -q tests/runtime/test_member_scenarios.py
uv run --no-sync pytest -q tests/runtime/test_surface_substitution.py tests/discovery
```

The broad suite after the refactor contains 38 tests. Test counts are descriptive,
not a reliability metric. Prefer assertions on outputs, refusal before delivery,
persisted results and session ownership over internal call order. Architecture
tests are the exception: they intentionally protect dependency rules.

Playwright can generate trusted DOM events, so the handoff integration test
simulates an operator's click in the same page. It verifies protocol behavior,
not the physical presence of a human. Historical real headed intervention and
real provider runs remain separately identified under `evidence/`.

When adding a surface, add real adapter acceptance tests under `surfaces/` and
reuse the public interface. When changing the language, test malformed operands
and wrong-input behavior as well as the happy path. Keep fixture injections and
fabricated provider decisions out of discovery's tool set.
