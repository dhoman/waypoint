# Implementation plan

## Package and interface refactor

- [x] Establish a behavior baseline and remove version 1 with user approval.
- [x] Separate domain, application wiring, discovery, runtime, surfaces, providers,
  evidence, inspector and demo packages; keep current CLI/artifact formats stable.
- [x] Make the surface/provider interfaces explicit and test substitution,
  ownership, strict isolation and current-engine safety scenarios.
- [x] Document execution, class relationships, dependency rules and extension steps;
  add contributor/agent instructions and a navigable documentation index.
- [x] Verify tests, installed-package resources and retained version-2 replay.
  Preserve historical evidence unchanged.

## General website correction

- [x] Add generic browser observation/targeting and runtime URL/action permissions.
- [x] Add version-2 artifacts with arbitrary typed inputs, learned recognition and extraction.
- [x] Add generic LLM discovery, deterministic replay and same-session handoff to the CLI.
- [x] Prove reuse against unrelated applications and a public site without changing engine code.
- [x] Update documentation and retain real evidence.

Version 1 remained readable at this milestone; the later package refactor
removed it at the user's request. New websites must not require
application-specific code, selectors or profiles before discovery.
Authentication, additional origins and consequential-action permissions remain
explicit runtime choices. Page content grants no authority.

## Initial implementation

- [x] Inspect the repository/environment and OpenAdapt; choose a direct adapter.
- [x] Build typed artifact, synthetic iframe application, surface and event contracts.
- [x] Execute real LLM discovery; compile and replay with different inputs.
- [x] Add bounded recognition, outcomes, policy and same-session human transfer.
- [x] Build artifact/run inspector and execute focused acceptance tests.
- [x] Complete verification, the evidence index, README and REPORT.

The repository had no assignment PDF, pre-existing stack or unrelated changes.
The user's requirements define the evaluation contract.

Use the existing uv-managed Python 3.12.13. Work in red/green/refactor vertical
slices through public interfaces, prioritizing output correctness, identity,
ambiguity, policy, bounded retries and resume ownership. Commit each coherent
milestone; do not publish or push. Schema scaffolding preceded the user's TDD
instruction; behavior changes follow it.
