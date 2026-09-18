# Architecture

Waypoint discovers bounded capabilities on websites supplied at runtime. The
default CLI accepts URL, goal and arbitrary named scalar inputs; no per-site
Python code, selector profile or output schema is required. Version 2's generic
observer exposes visible structural controls, headings, tables and a filtered
DOM outline. The LLM chooses actions and proposes recognition/extraction rules;
the executor validates them against the live UI. No tool exposes application
source, databases, private APIs or arbitrary JavaScript execution.

A real public-site discovery opened a bookstore category; model-blocked replay
opened a different category and extracted its displayed books. Browser tests also
cover an unrelated parts catalog and the synthetic member console's iframe.
Generic discovery also executed the full four-action iframe route and strict
replay returned member B's typed invoices and total of 100.00. Generic handoff
has a simulated-operator browser regression, not a new physical-human recording.
The original version-1 member-to-invoice demo/evidence remains readable via
explicit compatibility mode. Its four-action route, business branch and real
headed intervention are retained rather than represented as generic discovery.

The system uses Python/Pydantic, one async Playwright session owner, a small CLI,
JSON artifacts, JSONL events, and a standalone HTML/SVG inspector. The surface
interface hides browser objects; its implementation handles structural targeting,
reads, screenshots, observation, policy and session ownership. Discovery receives
a provider interface. Replay does not import discovery or its provider. The
strict entrypoint removes API credentials and actively blocks provider imports
and external Python connections; browser traffic has its own allowlist.

OpenAdapt flow 1.35.1 was inspected at commit
`cfea6ecd9540b78bafcdf6bb72887d61c2a59fc0`. Its structural and native-action seams
are useful references, but the actual synchronous browser adapter imports its
IR/resolver, and installation brings OCR/image-processing and other dependencies.
We implemented an independent async adapter. No source was copied. ADR 001 records
the inspected files, MIT license, separately licensed benchmark material, and
maintenance consequences. OpenAdapt's workflow control states are not our screen
catalog. The assignment PDF was unavailable; the supplied prompt was the brief.

# Artifact schema

Schema 2.0 separates reusable screens, task-specific control states/transitions,
and actual run evidence. Search before and after input uses one screen definition
with different progress. Member profiles share landmarks but require an exact
extracted Member ID equal to the mandatory input. Names, balances, and row counts
do not become screen types. Dialogs, loading and read-only access change behavior.

Artifacts include capability/revision, observed app title, origin, entry path,
surface, explicitly unasserted app version until reviewed,
typed input/output contracts, provenance, validation references, logical controls,
declarative recognition/identity predicates, guards, actions, expected and
alternative destinations, risk, deadlines and recovery policy. The language is
closed: role/label/text/title/placeholder/CSS locators, input references,
fill/select/click/press/check/extract/outcome actions, and explicit predicates.
Outputs use field, unique text/attribute, table, repeated list or numeric sum
rules with scalar/column types. There is no artifact-provided executable code.
Models reject unsupported types/references, missing nodes, unreachable terminals,
invalid bindings and unsafe retry declarations. Global visit/step bounds limit
cycles; this is not a general state-machine theorem prover.

Compilation preserves the observed route. Repeated screen equivalence is checked
against captured landmarks and remains draft until replay evidence exists.
Version-2 output and screen rules are model proposals checked by the executor;
exact displayed entity-field matches add input identity bindings. Rejected
proposals receive bounded discovery-only feedback, never an implicit replay fix.
For version 1, output contracts were authored and a subsequent revision adds
the unseen missing-member branch with authored provenance. Generic discovery
does not claim to discover branches it has not seen. The
qualification command requires matching artifact digests and coverage of every
transition, alternative destination and terminal. It produces separate validation
annotations, not an approval service or a claim that other routes do not exist.

# Determinism & error handling

Replay validates artifact/inputs, observes before each action, checks recognition
and identity, resolves a unique contextual target, enforces policy, and checks
destination/postconditions afterward. Multiple screen or guard matches are errors,
not list-order precedence. The executor checks visible identity again immediately
before acting. The missing-member condition returns a declared business outcome;
wrong identity and ambiguous targeting fail before the next relevant action.
Unknown observations retain screenshots/filtered snapshots and request intervention.

Visible loading uses a deadline-bound browser readiness predicate, not a fixed
sleep. No action resubmission is supported: only zero-retry artifacts are admitted.
A delivery ledger marks attempted delivery uncertain until postconditions are
verified and refuses repeated delivery. An isolated test loses acknowledgement
after a synthetic write and verifies that the receiver is invoked once. No write
is part of the main capability, and no generic reverse/reset edge is inferred.

Results distinguish success, business outcome, awaiting intervention, failure and
cancellation. Events correlate run, capability/revision, transition, recognition,
checks, evidence and timing. Model inference, observation/recognition, target
resolution, action, extra application wait and human wait are separated. Action
duration includes navigation acknowledgement. The inspector overlays actual
edges and links unexpected evidence to the affected transition. Sample sizes are
explicit; the demonstrations establish behavior, not statistical reliability.

# Heterogeneity & multi-tenant

The implemented surface is structural Chromium automation, not a site-specific
integration. A fresh discovery supplies application knowledge as artifact data.
Inputs and additional permissions are runtime configuration; the artifact pins
its discovery origin and entry path. Cross-origin replay requires rediscovery.
A future tenant/vendor
profile could override logical locator bindings and approved variants in a new
version, then revalidate outputs and identity. Changed landmarks, table headers,
version markers, ambiguity or identity fail closed as drift. Shared templates do
not authorize another tenant or relax origin/entity checks. Tenant authorization,
credential management and real-data redaction would be additional work.

A native adapter could translate observations and tagged native targets through
OpenAdapt structural/native seams, advertise which capture capabilities exist,
and preserve the same ownership and uncertainty contracts. DOM selectors would
not work unchanged on desktop. No desktop adapter was implemented or exercised.

# Escalation & handoff

Ownership moves through automation, awaiting human, human, validating resume and
terminal. The intervention describes run/capability, transition, state, reason and
sanitized evidence. A token-scoped CLI command transfers the same headed browser,
context and page to the operator. Automation is prohibited until a fresh resume
observation matches a permitted checkpoint, the requested entity and outgoing
guards. The operator may reach the invoice checkpoint directly; resume does not
assume the original node. Failed validation leaves human ownership intact, and
stale/duplicate commands are refused. Cancel yields a distinct terminal result.

The retained demonstration records the real in-page dismiss click and successful
resume. Input capture replaces values with a fixed redaction marker and is tested
separately. Browser chrome and OS activity are outside capture. Trusted DOM events
are not proof of physical human identity. No active artifact is modified; manual
changes would require a separately reviewed future revision.

# Safety

Policy lives outside the model/artifact. Generic control semantics, navigation
origins, frames, popups and request methods are checked. Defaults permit reads,
form input and recognizable navigation/search, but block consequential labels
and unclassified buttons. Explicit CLI permissions can add origins, methods and
exact control labels. This semantic heuristic cannot prove arbitrary GETs or
page scripts are read-only. Passive assets can load across origins; this is not
a hostile-site sandbox. The version-1 fixture retains its narrower route policy.
Close account is rejected even when submitted as an ordinary click. The model's
risk assertion is never authority. UI text is untrusted input to the discovery
prompt; all chosen operations still pass the executor's allowlist.

Evidence uses fake fixture data and a public scraping-practice bookstore, never
private customer data. Environment credentials, browser storage, raw provider
conversations and private reasoning are not persisted. Screenshots mask form
values, and event capture discards typed values. Visible synthetic identities are
retained to make failures auditable. This does not establish production-grade PII
removal or isolate malicious code on an allowed origin. Strict-mode Python guards
and browser request policy are not a substitute for an OS/network sandbox.

# Cuts

No global application discovery, arbitrary workflow designer, graph database,
queue, worker fleet, cloud deployment, tenant console or second surface. No OCR,
pixel fallback, automatic model repair, credential login, durable browser recovery,
write approval flow or generic Back/reset recovery. Draft artifacts are executable
for local validation; qualification is metadata, not a security approval gate.
No Linux desktop session was exercised here; headless/headed Playwright paths are
portable but must be checked on the evaluator's host. The macOS fixture and browser
scenarios, focused tests and inspector interaction were exercised locally. Evidence
documents commands, code provenance and early-run fingerprint limitations. The
repository and artifacts are local; nothing was published or submitted externally.
