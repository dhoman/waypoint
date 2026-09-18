# Extending Waypoint

Start with the [architecture](ARCHITECTURE.md) and [package map](../waypoint/README.md).
Do not add new root-level modules or resurrect a parallel engine for a new app.

## First choose the kind of extension

| You need… | Change here | Usually unchanged |
|---|---|---|
| Another website or read-only workflow | Run discovery; review a new artifact | Python source |
| Different runtime permissions/login | CLI configuration and manual preparation | Graph semantics |
| Another browser implementation with the same language | `surfaces/<name>/` and application wiring | Discovery/replay interpreters |
| Native desktop interaction | New surface package **and** deliberately versioned target/scope vocabulary | Ownership, delivery and much of graph interpretation |
| Another model provider | `providers/<name>.py`, application wiring | Replay and surface adapters |
| A new predicate/action/output operation | Domain language, interpreter, affected adapter(s), tests | Unrelated transports and operator UX |
| Another fixture or failure scenario | `demo/` or `tests/support/` | Agent tools and production policy |

## Adding a surface

### Placement and relationships

Create a cohesive package, for example:

```text
waypoint/surfaces/native/
├── __init__.py
├── session.py       Lifecycle, observations, targeting, actions, reads, capture
└── policy.py        Native process/window/control permissions
tests/surfaces/
└── test_native.py   Real adapter contract/safety tests on the supported host
```

This is a proposed layout, **not existing native support**. Add helpers only when
they hide real complexity; do not create one-line forwarding classes for every
method. Keep SDK objects, process handles and native targeting machinery inside
the adapter package.

The new session satisfies [Surface](../waypoint/surfaces/protocol.py). It does not
inherit from `Browser`, `Replay`, or an application-specific class. A `Protocol`
is a description of what callers need, not a plugin loader or default behavior.
An adapter may explicitly inherit the protocol for type checking, but no shared
implementation is supplied by doing so.

### Required interface and invariants

| Member | Required behavior |
|---|---|
| Async context manager | Create/close the controlled session exactly once; close resources on failure. The application owns lifetime; runners borrow it. |
| `binding` | Supply stable scope metadata for compilation. Browser schema 2 uses origin/entry path; do not invent a fake HTTP URL for a native application. |
| `capabilities` | Advertise only implemented features. Current engine needs structural observations/reads; this is not an automatic feature-negotiation framework. |
| `ownership` | Share one `Ownership` instance with the runner. All automation checks it before delivery; human control stays on the same session. |
| `event_sink` | Accept the injected trace sink. Emit sanitized correlated operational events, not secrets or SDK objects. |
| `validate_capability(cap)` | Reject wrong surface, incompatible target language or scope before artifact actions. Bind actual adapter policy, not a model risk label. |
| `observe()` | Return a normalized `Observation`: visible landmarks, fields, controls, tables, relevant transient/blocking facts. No private application state. |
| `resolve(target, inputs)` | Require exactly one contextual match or raise. Return plain resolution facts, never a live handle. |
| `act(action, inputs)` | Recheck ownership, blocking UI, uniqueness and concrete permissions before delivering. Wait within bounds; never retry uncertain delivery. |
| `read(...)`, `read_rows(...)` | Read displayed values using explicit targets and limits; refuse missing/ambiguous/unsupported reads. No arbitrary expression evaluation. |
| `settle(timeout_s)` | Observe readiness within a deadline, including known loading states. Do not hide blind action retries here. |
| `capture(directory, name)` | Return relative evidence references, with capture/redaction applied at this point. An adapter without screenshot support can return available structured evidence or none. |

The runner owns graph guards, entity predicates, destination/postcondition checks,
uncertainty tracking and permitted resume checkpoints. The adapter owns concrete
targeting, actuation, scope policy, readiness and session event capture. Do not
duplicate the workflow interpreter inside the adapter.

### What is already substitutable, and what still needs design

Discovery and replay accept a surface object, not a Playwright object or URL.
Compilation accepts `SurfaceBinding`, not a concrete adapter. Tests run both
discovery and replay with [MemorySurface](../tests/support/memory_surface.py),
which has no page, locator or URL. This validates the execution seam.

However, **schema 2 only admits `surface='browser'` and browser `Target` tags**.
Its `origin`/`entry_path`, headings/tables and locator vocabulary reflect the one
implemented production surface. A native adapter is therefore not just dropping
in another Python file:

1. Define a versioned scope/target representation appropriate to native process,
   window, accessibility or visual identifiers. Use distinct tagged models;
   never disguise UIA or coordinates as CSS.
2. Update artifact validation deliberately, including incompatible-target and
   scope checks. Define which predicates/extractions the native observations can
   support; unsupported operations must stop explicitly.
3. Ensure discovery decisions can propose the new tags and policy checks them.
   Add provider/prompt support for the language without allowing arbitrary code.
4. Implement the surface contract and host-specific safety tests. Decide and
   document actual manual-event capture limitations before advertising them.
5. Add explicit construction/selection in `app/workflow.py` and CLI options in
   `app/cli.py`. Do not put adapter selection inside the replay loop. No registry
   is necessary until there is a real plugin requirement.
6. Discover/revalidate artifacts for the new surface. A shared screen concept
   does not make DOM locators portable or authorize cross-tenant execution.

The [OpenAdapt ADR](adr-001-surface.md) is the starting point for native backend
research. Do not claim that wrapping an unexercised backend creates working
desktop support.

### Adapter acceptance checks

Test public behavior on a real controlled target where available:

- Same workflow, different typed input → actual displayed output for that input.
- Wrong entity and duplicate targets → stop before the next relevant action.
- Unsupported surface/locator and denied process/origin/control → reject before delivery.
- Slow/transient UI → bounded readiness; unsupported state → evidence and stop.
- Human ownership → automation refused; fresh valid checkpoint → resume in the
  same session; stale/duplicate token → refuse.
- Redacted manual inputs, useful failure evidence, cleanup on errors.
- Uncertain action delivery → no resubmission.

Use the in-memory adapter for interpreter tests, not as evidence that a real
platform works. The browser scenario tests show how developer fixture injection
is kept out of discovery tools.

## Adding a provider

Implement the small [Provider](../waypoint/discovery/models.py) interface:
`name`, `model`, and async `decide(goal, inputs, observation, history) -> Decision`.
Place the transport under `providers/`, keeping SDK-specific serialization and
timeouts there. Use [OpenAIProvider](../waypoint/providers/openai.py) as the existing
example; its decision type and instructions are supplied by the application.

Create the provider only in the discovery branch of `app/workflow.py`. Add an
explicit selection option if needed; do not import a provider in runtime,
artifact loading, CLI help or offline inspection. `app/isolation.py` blocks the
entire `waypoint.providers` and `waypoint.discovery` namespaces during strict
replay, so new internal provider modules do not accidentally bypass the guard.
Review additional external SDK names/network mechanisms as part of the change.

Mock only the external model seam. Tests should drive a real discovery loop
with typed test decisions and check accepted actions/artifacts or safe failure.
Record real-model acceptance separately, with credentials in the environment,
not tests/logs/artifacts. Test-provider traces are never genuine discovery evidence.

## Extending the declarative language

Start in [domain/artifact.py](../waypoint/domain/artifact.py), with one focused
failing behavior test. Add an allowlisted operation and operand/reference
validation, then deterministic interpretation in `runtime/interpret.py` and
adapter support where appropriate. Discovery should use those same semantics to
validate proposals; do not maintain a looser parallel interpreter for the model.

Preserve artifact fingerprints for an unchanged language. When meaning or shape
changes, explicitly version it and describe compatibility/migration. Do not
execute model/artifact-supplied Python or JavaScript, infer precedence between
overlapping guards, or turn an unknown observation into approved graph data.

## Small programmatic example

The application normally constructs these dependencies. A caller can also borrow
the same public interface directly:

```python
import asyncio
from pathlib import Path

from waypoint.domain.artifact import Capability
from waypoint.evidence.trace import Trace
from waypoint.runtime.replay import Replay
from waypoint.surfaces.browser.session import Browser

async def main():
    cap = Capability.model_validate_json(
        Path("evidence/web-member-discovery-6/capability.json").read_text()
    )
    async with Browser(cap.origin + cap.entry_path, headed=True) as surface:
        result = await Replay(
            cap, surface, {"memberId": "M-202"}, Trace("runs/programmatic", cap)
        ).run()
        print(result.status, result.outputs)

asyncio.run(main())
```

Start the fixture on port 8770 first; use a fresh trace directory. This does not
install strict-process guards or implement a terminal handoff loop. Use the
documented CLI for strict replay and interactive operator control. No inheritance
or subclassing is required to wire these objects together.
