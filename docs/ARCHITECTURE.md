# Architecture and execution

Waypoint separates **what a workflow permits**, **what happened during a run**,
and **how a particular surface is controlled**. Read the [package map](../waypoint/README.md)
alongside this document for exact definitions and source links.

## The three models

| Model | Owns | Does not mean |
|---|---|---|
| Screen catalog (`Screen`) | Recognition predicates, identity bindings and proposal/validation provenance | One node per member, balance or observed visit |
| Capability graph (`State`, `Transition`, `Capability`) | Task progress, allowed actions, guards, destinations, outcomes and extraction rules | A complete map of the application or inferred reverse navigation |
| Run evidence (`Observation`, `Result`, `Trace`) | What was visible, checks/actions, timings, outcomes and interventions | Automatic approval of unexpected screens or edited graph edges |

For example, two control states can both reference the member-search screen:
one before filling the field and one before submitting it. Two different members
share the profile screen definition. A separate field-to-input predicate must
verify which member is displayed. Matching a screen is not authority to act on
any entity on that screen.

The artifact is deliberately data, not a recording transcript or executable
Python/JavaScript. `domain/artifact.py` defines the allowlisted predicates,
actions, locators and output extraction rules. Pydantic rejects unknown fields,
invalid references, unsupported tags, unreachable states and nonzero retries.
An explicit step budget bounds control flow; this is not a theorem prover.

## Dependency direction

```text
cli.py / strict.py
        │
        ▼
app/                  constructs concrete dependencies; owns session lifetime
  ├── discovery/      Provider → decision → checked action → draft artifact
  ├── runtime/        artifact + inputs → checked transitions → result
  ├── surfaces/browser/   implements Surface using Playwright + Policy
  ├── providers/openai.py implements Provider using the optional SDK
  ├── evidence/       trace persistence / qualification
  ├── inspector/      offline read-only view
  └── demo/           separate developer-owned target

discovery/ and runtime/ → surfaces/protocol.py (never a concrete adapter)
all data consumers     → domain/ (no I/O, SDKs or application imports)
```

`discovery/` reuses `runtime/interpret.py` to validate proposals against the same
declarative semantics replay uses. The reverse dependency is forbidden: runtime
must not import discovery, a model SDK, provider, CLI, demo, or concrete surface.
The surface interface shares `Ownership` from `runtime/ownership.py`; that small
module is independent of the replay engine. Browser evidence capture uses the
shared sanitization functions, not its own competing redaction implementation.

`app/workflow.py` is the composition root. It is intentionally where concrete
browser/provider choices are made. There is no plugin registry, dependency
injection framework or global route planner. Adding one adapter does not justify
introducing those systems. Dependency tests protect these rules.

## Class relationships

There is very little inheritance. Most relationships are composition or typed
data references; sharing a directory does not mean one file extends another.

| Relationship | Meaning |
|---|---|
| `Model` extends Pydantic `BaseModel` | Common validation configuration (`extra='forbid'`). |
| Artifact/observation/provenance models extend `Model` | Validated data, not active services. |
| `Decision` / `ScreenProposal` extend `Model` | Constrained provider output; separate from published artifact data. |
| `Browser` satisfies `Surface` | Structural interface implementation; **not** a subclass of the protocol or of the runner. |
| `OpenAIProvider` satisfies `Provider` | Model transport selected and injected by application wiring. |
| `Replay` holds `Capability`, `Surface`, `Trace`, `DeliveryLedger` | Interpreter with borrowed dependencies, not a browser-derived class. |
| `Browser` holds `Policy`, `Ownership`, Playwright session objects | Encapsulates concrete targeting, I/O and control ownership. |
| `Replay` and `Browser` refer to the **same** `Ownership` | Prevents independent notions of who may act. |
| `Trace` holds an optional `Capability` | Correlates metadata/fingerprints; it does not execute the graph. |

The [in-memory test adapter](../tests/support/memory_surface.py) satisfies the same
surface interface without a browser, page or URL. It tests substitution using
the existing browser-shaped declarative vocabulary; it is not a native adapter.
Python `Protocol` describes structural typing, not automatic runtime enforcement
or a guarantee that an implementation is safe. Behavioral contract tests matter.

## Execution walkthrough

### Discovery

1. `app/cli.py` parses `discover`; `app/workflow.py` validates named scalar inputs
   and builds the browser's runtime policy and `Trace`.
2. The application opens one `Browser` using `async with`. That object owns its
   Playwright process, context and page until the command ends. Optional manual
   preparation occurs in this same session.
3. Only on this branch, the application imports the provider SDK, `Decision`
   schema, generic prompt and discovery loop.
4. `discover()` observes through `Surface`. The provider sees the goal, explicit
   input bindings, visible structural observation and prior operational actions.
   It has no source-code, database, private API or arbitrary-script tool.
5. The provider returns a `Decision`. The loop checks proposed recognition and
   identity predicates, input references and unique target resolution. Rejected
   pre-action proposals receive feedback without delivering the action. Deadlines,
   step limits and repeated-no-progress checks bound this process.
6. For an accepted action, `Surface.act()` enforces ownership and adapter policy,
   resolves the target again, performs the operation and waits within a deadline.
   Pre/post observations and timings become trace events.
7. On `finish`, extraction rules are evaluated against the UI. The compiler gets
   accepted observations, actions, screen proposals, output rules and an
   adapter-supplied `SurfaceBinding`. It compiles a draft capability independently
   of conversation formatting. Nothing silently becomes a validated branch.

`SurfaceBinding` contains the current artifact's scope metadata (`surface`,
`origin`, `entry_path`). The browser computes it from the configured entry URL.
The compiler no longer imports URL policy or accesses a live browser. The current
schema still restricts surface/target tags to browser; extending that language
is explicit work, described in the extension guide.

### Replay

1. Optionally, `app/isolation.py` installs strict import/network guards **before**
   entering the CLI. It actively probes the prohibitions and writes proof.
2. The application loads a schema-2 artifact, validates exact input names/types,
   constructs a runtime policy and opens the session. There is no provider.
3. `Replay` revalidates the artifact and asks `Surface.validate_capability()` to
   reject the wrong adapter or target scope before artifact actions begin.
4. The runner observes, recognizes the screen, checks entity identity, and selects
   exactly one outgoing transition with matching guards. It observes again before
   delivery. Multiple matches are errors, never incidental list-order choices.
5. The adapter enforces concrete action policy and uniqueness. The runner tracks
   delivery, checks the expected destination/postconditions, and advances progress.
   Extraction reads displayed data and converts values according to typed rules.
6. The runner writes `succeeded`, `business_outcome`, `awaiting_intervention`,
   `failed`, or `cancelled`, with outputs/business code or failure details.

Unknown observations get evidence and an intervention request, not a new screen
definition. Identity mismatch, ambiguous targeting or policy violations fail
closed. A known business outcome requires an explicit artifact transition; the
test support's missing-member branch demonstrates authored data, not a second
engine implementation. A transient is handled by bounded adapter readiness;
remaining unknown/transient states stop rather than guess.

There is no retry of a delivered action. `DeliveryLedger` treats attempted
delivery as uncertain until checks confirm it. Handoff cannot authorize a blind
resubmission. Navigation reset would not reset business data, and no generic
Back/reset behavior exists.

### Handoff

```text
automation → awaiting_human → human → validating_resume → automation
                                  ↖ rejected resume ───┘
any completed/cancelled run → terminal
```

The runner requests intervention and emits permitted checkpoints. With headed
interactive replay, the application keeps the **same** context/page alive and
accepts token-scoped terminal commands. The adapter captures relevant in-page
click/input events only during human ownership. Input values are redacted.

Resume requires a fresh observation and a unique permitted checkpoint with valid
identity and outgoing guards. The operator need not return to the original state.
A rejected resume leaves human ownership intact; a successful token cannot be
used again. Browser chrome and OS interactions are not captured. Noninteractive
paused commands save their result and close; they are not durable resumable jobs.

## Evidence and inspection

`Trace` correlates events by run/capability/revision and records a canonical
artifact hash plus a recursive Python/HTML/JS source hash. Refactoring changes
the source hash, but retained schema-2 artifact hashes are checked unchanged by
tests. Historical evidence is never rewritten to imply it ran newer code.

`qualify()` checks matching fingerprints and coverage of terminals, transitions
and alternative destinations, then returns a separately annotated artifact.
Validation is not a security approval service or a reliability estimate.

`render_inspector()` reads artifact/run files and embeds them in a standalone
HTML/SVG page. Selecting an edge shows its contract and actual events; unexpected
observations remain linked evidence. The inspector has no automation session,
model dependency or graph editor. Its template and the browser observer are
package resources, verified in a built wheel.

## Trust and current limits

UI/model output is untrusted. Declarative validation and adapter policy are
independent of model risk labels. Browser policy limits origins, methods and
control semantics, but passive assets can cross origins and allowed scripts/GET
handlers are not proven harmless. Strict Python guards are not an OS sandbox.

The evidence policy is for synthetic/public data, not production PII. Masking
form controls does not redact all visible identities, screenshots or page text.
No desktop adapter, production authentication store, multi-tenant approval
system, distributed worker, global planner or automatic replay repair exists.
The user-approved retirement removed schema-1 code and flags; old JSON/static
inspectors remain historical records only.
