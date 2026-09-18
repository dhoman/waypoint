# Package map

This is a responsibility-based layout, not a file-per-application layout.
There is one engine. `__init__.py` files only identify packages; they deliberately
do not re-export everything or import optional SDKs as a side effect.

```text
waypoint/
├── cli.py, strict.py         Stable module/console launchers
├── app/                     Argument parsing and concrete dependency wiring
├── domain/                  Typed artifact and observation vocabulary
├── discovery/               Model-guided loop, decisions, prompt and compiler
├── runtime/                 Model-free replay, interpretation and session safety
├── surfaces/
│   ├── protocol.py          Surface interface and adapter-provided binding
│   └── browser/             Playwright session, browser policy and observation JS
├── providers/               Model transport adapters
├── evidence/                Trace persistence, redaction and qualification
├── inspector/               Offline renderer and bundled HTML template
└── demo/                    Developer-owned synthetic application
```

## Entrypoints and application wiring

| File | Important definitions | Responsibility / callers |
|---|---|---|
| [cli.py](cli.py) | `main` import | Preserves `waypoint` and `python -m waypoint.cli`; no workflow logic. |
| [strict.py](strict.py) | `main` import | Preserves `python -m waypoint.strict`. |
| [app/cli.py](app/cli.py) | `main`, `load_capability` | Parses commands, rejects retired schema versions, dispatches fixture/inspection/qualification/workflow commands. |
| [app/workflow.py](app/workflow.py) | `execute`, `parse_inputs` | Composition root: constructs policy, browser session, trace and either a provider or replay runner. Owns the session's `async with` lifetime. |
| [app/handoff.py](app/handoff.py) | `interact` | Terminal `take/resume/cancel` interaction; delegates safety rules to `Replay`/`Ownership`. |
| [app/isolation.py](app/isolation.py) | `NoModels`, `install`, `proof`, `main` | Removes model credentials; rejects discovery/provider imports and external Python sockets; writes isolation proof. |

## Models, learning and execution

| File | Important definitions | Responsibility / callers |
|---|---|---|
| [domain/base.py](domain/base.py) | `Model`, `Provenance` | Pydantic base with unknown fields forbidden; discovery/authored/inferred provenance. No I/O. |
| [domain/artifact.py](domain/artifact.py) | `Capability`, `Screen`, `State`, `Transition`, `Predicate`, `Action`, `Target`, `Extraction`, `Column`, `Observation`, `Result` | Closed schema-2 language, graph checks and typed input validation. Used across the system. |
| [discovery/models.py](discovery/models.py) | `Decision`, `ScreenProposal`, `Provider` | Structured model output and structural provider interface. Imports no model SDK. |
| [discovery/prompt.py](discovery/prompt.py) | `PROMPT` | Generic operating instructions; no per-site routes. Loaded only for discovery. |
| [discovery/loop.py](discovery/loop.py) | `discover`, `parameterize` | Observe/decide/validate/act loop; bounded proposal feedback; exact input bindings; evidence collection. Receives a `Surface` and `Provider`. |
| [discovery/compiler.py](discovery/compiler.py) | `compile_route` | Converts accepted observations/actions/proposals into a draft graph. Receives `SurfaceBinding`, not a browser or URL parser. No model calls. |
| [runtime/replay.py](runtime/replay.py) | `Replay` | Validates and executes saved graphs, chooses unambiguous transitions, records results, requests intervention and validates resume. Receives a `Surface`, never constructs one. |
| [runtime/interpret.py](runtime/interpret.py) | `holds`, `check`, `recognize`, `extract`, `convert` | Deterministic predicate/output interpreter. Uses normalized observations and the surface's read/resolve methods. |
| [runtime/ownership.py](runtime/ownership.py) | `Ownership` | Single-owner state machine and one-use resume tokens; shared by runner and adapter. |
| [runtime/delivery.py](runtime/delivery.py) | `DeliveryLedger` | Tracks uncertain versus confirmed delivery and refuses resubmission. |

## Interaction and model adapters

| File | Important definitions | Responsibility / callers |
|---|---|---|
| [surfaces/protocol.py](surfaces/protocol.py) | `Surface`, `SurfaceBinding`, `Resolution` | Contract used by discovery/runtime; lifecycle, scope validation, observations, actions, reads, evidence and ownership. |
| [surfaces/browser/session.py](surfaces/browser/session.py) | `Browser` | Concrete session adapter: owns Playwright/browser/context/page, targets frames, waits for readiness, captures manual events and evidence. Raw Playwright handles stay here. |
| [surfaces/browser/policy.py](surfaces/browser/policy.py) | `Policy`, `origin` | Browser-specific origin/method/control authorization. Consulted before actions and requests. |
| [surfaces/browser/observe.js](surfaces/browser/observe.js) | fixed observation function | Filtered visible structure. Trusted adapter implementation, not arbitrary code supplied by a model/artifact. Packaged beside `session.py`. |
| [providers/openai.py](providers/openai.py) | `OpenAIProvider` | Optional Responses transport. Decision type and instructions are injected, not coupled to an application. SDK import is discovery-only. |

`Browser` does **not** extend `Surface` or `Replay`. It satisfies `Surface` by
providing its members (Python structural typing). `OpenAIProvider` similarly
satisfies `Provider`. See [class relationships](../docs/ARCHITECTURE.md#class-relationships).

## Evidence, inspection and the target application

| File | Important definitions | Responsibility / callers |
|---|---|---|
| [evidence/trace.py](evidence/trace.py) | `Trace`, `sanitized`, `sanitize_manual_event`, `source_digest` | Correlated JSONL events/results, canonical artifact fingerprint and recursive source fingerprint; synthetic/public-data evidence handling. |
| [evidence/qualification.py](evidence/qualification.py) | `qualify` | Requires matching artifact fingerprints and graph coverage; returns a separate annotated artifact without mutating its input. |
| [inspector/render.py](inspector/render.py) | `render_inspector` | Embeds artifact/run data and constrained evidence references into an offline page; no browser automation. |
| [inspector/template.html](inspector/template.html) | HTML/CSS/SVG/JS view | Node/edge selection, actual-run overlay, evidence, outcomes and timings. Packaged beside the renderer. |
| [demo/member_console.py](demo/member_console.py) | `FixtureServer`, `Handler` | Fake member/invoice application and developer failure injection. Not imported by the engine or exposed as an agent tool. |

## Where changes belong

- A workflow on another website: discover a new artifact, not a new package.
- A new interaction technology: `surfaces/<name>/`, not a root file or browser subclass.
- A model transport: `providers/<name>.py`, wired in `app/workflow.py` only.
- New declarative semantics: `domain/artifact.py` plus the corresponding interpreter
  and adapter support, with versioning and negative tests.
- Operator UX: `app/handoff.py`; ownership/resume rules stay in `runtime/`.
- A new demo: `demo/`; a test-only adapter/fixture: `tests/support/`.

The old flat modules and `waypoint/web/` were removed. Internal Python imports
are not shimmed. Existing schema-2 JSON artifacts retain their canonical hashes;
schema-1 data remains historical only. The [extension guide](../docs/EXTENDING.md)
explains the remaining schema work required before native targets can be added.
