# Architecture

Waypoint discovers bounded capabilities from a URL, goal and arbitrary named
scalar inputs, without per-site Python code, selector profiles or output
schemas. The version-2 observer exposes visible structural controls, headings,
tables and a filtered DOM outline. The LLM chooses actions and proposes
recognition/extraction rules; the executor validates them against the live UI.
No tool exposes application source, databases, private APIs or arbitrary
JavaScript execution.

A real discovery on a public bookstore opened a category; model-blocked replay
opened a different category and extracted its displayed books. Browser tests also cover
an unrelated parts catalog and the synthetic member console's iframe. Discovery
executed the four-action iframe route; strict replay returned member B's typed
invoices and total of 100.00. Generic handoff has a simulated-operator browser
regression test, but no new physical-human recording. Version 1 was retired at
the user's request. Its evidence/static inspector is historical, not a runnable
compatibility mode or evidence of new generic discovery.
Current-engine tests cover business branches and safety behavior.

The system uses Python/Pydantic, one async Playwright session owner, a CLI, JSON
artifacts, JSONL events, and a standalone HTML/SVG inspector. The surface
interface hides browser objects; its implementation handles structural
targeting, reads, screenshots, observation, policy and session ownership.
Discovery receives a provider interface. Replay does not import discovery or its
provider. The strict entrypoint removes API credentials and blocks provider
imports and external Python connections; browser traffic has its own allowlist.

Packages separate `domain`, `discovery`, `runtime`, `surfaces`, `providers`,
`evidence`, `inspector`, `app` and `demo`. Application wiring constructs
adapters; engines consume structural protocols and never import concrete
adapters. The browser and a test-only in-memory adapter verify that interface.
Class relationships, execution and extension steps are documented in
`docs/ARCHITECTURE.md`, `docs/EXTENDING.md` and `waypoint/README.md`.

OpenAdapt flow 1.35.1 was inspected at commit
`cfea6ecd9540b78bafcdf6bb72887d61c2a59fc0`. Its structural and native-action
interfaces informed the design. Its synchronous browser adapter imports its
IR/resolver, and installation adds OCR/image-processing and other dependencies.
We implemented an independent async adapter without copying source. ADR 001
records the inspected files, MIT license, separately licensed benchmark
material, and maintenance consequences. OpenAdapt's workflow control states are
not our screen catalog. The assignment PDF was unavailable; the supplied prompt
was the brief.

# Artifact schema

Schema 2.0 separates reusable screens, task-specific control states/transitions,
and run evidence. Search before and after input uses one screen definition with
different progress. Member profiles share landmarks but require the extracted
Member ID to equal the mandatory input exactly. Names, balances and row counts
do not become screen types. Dialogs and loading are explicit observation facts;
access variants require applicable artifact predicates rather than implicit
rules.

Artifacts include capability/revision, observed app title, origin, entry path,
surface, app version left unasserted until review, typed input/output contracts,
provenance, validation references, logical controls, declarative
recognition/identity predicates, guards, actions, expected and alternative
destinations, risk, deadlines and recovery policy. The closed language allows
role/label/text/title/placeholder/CSS locators, input references,
fill/select/click/press/check/extract/outcome actions, and explicit predicates.
Outputs use field, unique text/attribute, table, repeated list or numeric sum
rules with scalar/column types. There is no artifact-provided executable code.
Models reject unsupported types/references, missing nodes, unreachable
terminals, invalid bindings and unsafe retry declarations. Global step bounds
limit cycles without proving general state-machine properties.

Compilation preserves the observed route. Repeated screen equivalence is checked
against captured landmarks and remains draft until replay evidence exists. Exact
displayed entity-field matches add input identity bindings. Rejected
screen/output proposals receive bounded discovery-only feedback; replay never
repairs them. The current-engine test fixture adds a missing-member branch as
explicit authored artifact data. Discovery does not infer unseen branches, and
the fixture-specific amendment command was removed. Qualification requires
matching artifact digests and coverage of every transition, alternative
destination and terminal. It produces separate validation annotations without
granting approval or ruling out other routes.

# Determinism and error handling

Replay validates the artifact and inputs, observes before each action, checks
recognition and identity, resolves a unique contextual target, and enforces
policy. It rechecks visible identity immediately before acting and
destination/postconditions afterward. Multiple screen or guard matches fail
instead of using list order. An explicitly modeled missing-member branch returns
a business outcome; wrong identity and ambiguous targeting fail before the next
relevant action. For unknown observations, replay saves screenshots/filtered
snapshots and requests intervention.

Visible loading uses a browser readiness predicate with a deadline rather than a
fixed sleep. Only zero-retry artifacts are admitted. A delivery ledger refuses
resubmission and marks attempted delivery uncertain until postconditions are
verified. An isolated test simulates lost acknowledgement after a synthetic
write and verifies that the receiver is invoked once. No write is part of the
main capability. No generic Back/reset recovery exists, and no reverse/reset edge
is inferred.

Results distinguish success, business outcome, awaiting intervention, failure
and cancellation. Events correlate run, capability/revision, transition,
recognition, checks, evidence and timing. Timings separate model inference,
observation/recognition, target resolution, action, extra application wait and
human wait. Action duration includes navigation acknowledgement. The inspector
overlays actual edges and links unexpected evidence to the affected transition.
Sample sizes are explicit; the demonstrations do not establish statistical
reliability.

# Application and tenant variation

Structural Chromium automation uses application knowledge from discovery
artifacts. Inputs and additional permissions are runtime configuration; the
artifact pins its discovery origin and entry path. Cross-origin replay requires
rediscovery. A future tenant/vendor profile could override logical locator
bindings and approved variants in a new version, then revalidate outputs and
identity. Changed landmarks, table headers, version markers, ambiguity or
identity cause replay to fail closed as drift. Shared templates do not authorize
another tenant or relax origin/entity checks. Tenant authorization, credential
management and real-data redaction would be additional work.

A native adapter could translate observations and tagged native targets through
OpenAdapt structural/native interfaces, report its capture capabilities, and
preserve the same ownership and uncertainty contracts. DOM selectors would not
work unchanged on desktop. No desktop adapter was implemented or exercised.

# Escalation and handoff

Ownership moves through automation, awaiting human, human, validating resume and
terminal. The intervention describes run/capability, transition, state, reason
and sanitized evidence. A token-scoped CLI command transfers the same headed
browser, context and page to the operator. Automation is prohibited until a
fresh resume observation matches a permitted checkpoint, the requested entity
and outgoing guards. The operator may reach the invoice checkpoint directly;
resume does not assume the original node. Failed validation leaves human
ownership intact, and stale/duplicate commands are refused. Cancel yields a
distinct terminal result.

The retained demonstration records the in-page dismiss click and successful
resume. Input capture replaces values with a fixed redaction marker and is
tested separately. Browser chrome and OS activity are outside capture. Trusted
DOM events are not proof of physical human identity. No active artifact is
modified; manual changes would require a separately reviewed future revision.

# Safety

Policy runs outside the model/artifact and checks control semantics, navigation
origins, frames, popups and request methods. Defaults permit reads, form input
and recognizable navigation/search, but block consequential labels and
unclassified buttons. Explicit CLI permissions can add origins, methods and
exact control labels. This heuristic cannot prove arbitrary GETs or page scripts
are read-only. Passive assets can load across origins. Strict-mode Python guards
and browser request policy cannot isolate malicious code on an allowed origin or
replace an OS/network sandbox. The fixture-specific policy was retired. Close
account is rejected even when submitted as an ordinary click. The model's risk
assertion grants no authority. The discovery prompt treats UI text as untrusted
input; the executor checks all chosen operations against its allowlist.

Evidence uses fake fixture data and a public scraping-practice bookstore, never
private customer data. Environment credentials, browser storage, raw provider
conversations and private reasoning are not persisted. Screenshots mask form
values, and event capture discards typed values. Visible synthetic identities
are retained to make failures auditable. This is not production-grade PII
removal.

# Scope limits

The implementation excludes global application discovery, an arbitrary workflow
designer, a graph database, queues, worker fleets, cloud deployment, a tenant
console and a second surface. It also excludes OCR, pixel fallback, credential
login, durable browser recovery and write approval flows. Draft artifacts can
run for local validation. No Linux desktop session was exercised here;
headless/headed Playwright paths are portable but must be checked on the
evaluator's host. The macOS fixture and browser scenarios, focused tests and
inspector interaction were exercised locally. Evidence documents commands, code
provenance and early-run fingerprint limitations. The repository and artifacts
are local; nothing was published or submitted externally.
