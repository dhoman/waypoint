# Implementation plan

## Package and extension-point refactor

- [x] Baseline behavior; remove the retired version-1 implementation (user-approved).
- [x] Separate domain, application wiring, discovery, runtime, surfaces, providers,
  evidence, inspector and demo packages; keep current CLI/artifact formats stable.
- [x] Make the surface/provider interfaces explicit and test substitution,
  ownership, strict isolation and current-engine safety scenarios.
- [x] Document execution, class relationships, dependency rules and extension steps;
  add contributor/agent instructions and a navigable documentation index.
- [x] Verify tests, installed-package resources and retained version-2 replay;
  commit coherent milestones. Historical evidence is retained, not rewritten.

## General website correction

- [x] Generic browser observation/targeting and runtime URL/action permissions.
- [x] Version 2 artifact with arbitrary typed inputs, learned recognition and extraction.
- [x] Generic LLM discovery, deterministic replay and same-session handoff in the CLI.
- [x] Prove reuse against unrelated applications and a public site without changing engine code.
- [x] Update documentation, retain real evidence, and commit verified milestones.

At this earlier milestone version 1 remained readable; the package refactor above
supersedes that choice and removes it at the user's request. New websites must not require
application-specific code, selectors or profiles before discovery. Authentication,
additional origins and consequential-action permissions remain explicit runtime
choices rather than authority inferred from page content.

- [x] Inspect repository/environment and OpenAdapt; choose narrow direct adapter.
- [x] Build typed artifact, synthetic iframe application, surface and event contracts.
- [x] Execute genuine LLM discovery; compile and replay with different inputs.
- [x] Add bounded recognition, outcomes, policy and same-session human transfer.
- [x] Build artifact/run inspector and execute focused acceptance tests.
- [x] Finish final verification and evidence index; README / REPORT complete.

No assignment PDF was supplied in this repository. The user-provided requirements
are the evaluation contract. No pre-existing stack or unrelated changes exist.

Use the existing uv-managed Python 3.12.13. Work in red/green/refactor vertical
slices through public interfaces, prioritizing output correctness, identity,
ambiguity, policy, bounded retries and resume ownership. Commit each coherent
milestone; do not publish or push. Schema scaffolding preceded the user's TDD
instruction; behavioral implementation follows it.
