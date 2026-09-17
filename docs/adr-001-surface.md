# ADR 001 — Direct async browser adapter, OpenAdapt as reference

Accepted 2026-09-17. Inspected OpenAdaptAI/openadapt-flow commit
`cfea6ecd9540b78bafcdf6bb72887d61c2a59fc0`, package version 1.35.1.
Read DESIGN.md, docs/design/WORKFLOW_PROGRAM_IR.md, docs/SURFACES.md,
LICENSE, pyproject.toml and actual backend.py, ir.py and
backends/playwright_backend.py interfaces/imports.

The public Backend protocol is screenshot / coordinate / keyboard oriented.
StructuralActionBackend adds locator capture and resolution, with explicit
ambiguity refusal; NativeStructuralActionBackend adds native actuation receipts.
StructuralLocator includes DOM selector/frame path, role/name and native IDs.
The browser implementation is synchronous and imports the full IR and runtime
resolver. Base installation includes numpy, OpenCV, OCR, cryptography and
openadapt-types; wrapping it is not an isolated Playwright dependency.

Decision: implement our own small async Surface protocol and Playwright adapter.
No OpenAdapt source copied or vendored. Its MIT license permits reuse; the checkout
also includes separately licensed AGPL benchmark deployment files, which we do
not use. No OpenAdapt runtime dependency or notices are needed for original code.

Their Workflow.program states describe control flow (action, branch, loop, etc.),
not our reusable catalog of application screens. Their documented demonstrated
parameter defaults are inappropriate here: memberId must always be supplied.
We adopt the conceptual boundaries of structural uniqueness, identity gates,
effect uncertainty and surface binding, not the full compiler/governance stack.

A future native adapter would implement lifecycle, observations, tagged native
targets, unique resolution, actuation, evidence and control transfer; it could
wrap those public OpenAdapt structural/native interfaces on a dedicated owner
thread. It must advertise capture limitations and be exercised before claiming
support. DOM targets never silently translate to UIA or pixels. Requalification
is required for each app, profile, version and surface.

Maintenance: we own browser observation and target semantics; a pinned dependency
lock and contract tests cover that cost. Reassess wrapping only when native work
is actually in scope. No OpenAdapt installation was attempted because source
inspection established the dependency/ownership mismatch.

References: https://github.com/OpenAdaptAI/openadapt-flow/tree/cfea6ecd9540b78bafcdf6bb72887d61c2a59fc0
