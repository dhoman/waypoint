# Working in this repository

## Start here

- Read `README.md` for runnable commands, `waypoint/README.md` for file ownership,
  `docs/ARCHITECTURE.md` for execution and relationships, and `CONTRIBUTING.md`
  for changes.
- The engine supports only schema 2.0. Version-1 code and `--member`/`amend` modes
  were removed. Keep their evidence as historical records; do not restore the
  implementation or obsolete commands.
- Use the existing uv-managed Python and `.venv`; preserve unrelated changes.

## Placement and design

- `domain/`: validated declarative data; no I/O or adapter imports.
- `discovery/`: model loop, decisions and compilation. `runtime/`: model-free
  interpretation, ownership and delivery safety.
- `surfaces/protocol.py`: execution interface. Concrete adapters live in
  `surfaces/<name>/`; model transports live in `providers/`.
- Construct concrete dependencies in `app/workflow.py`. Keep root `cli.py` and
  `strict.py` as stable launchers without workflow logic.
- `evidence/`, `inspector/`, `demo/`: persistence, offline UI and synthetic target,
  respectively. Demo/private state is not an agent tool.
- Prefer composition and structural protocols to inheritance. Keep raw SDK
  objects inside adapters. New sites normally need artifacts, not engine changes.

## Verification and safety

- Use test-first vertical slices for behavior changes; refactor only from a
  passing baseline. Put tests under the owning area in `tests/`.
- Run `.venv/bin/pytest -q`, `.venv/bin/ruff check waypoint tests`, and
  `.venv/bin/ruff format --check waypoint tests` before handoff.
- Do not weaken identity, ambiguity, policy, ownership or uncertain-delivery
  checks. Strict replay must not import discovery/providers or call a model.
- Keep schema-2 artifact hashes stable for behavior-preserving changes.
- Do not fabricate real discovery evidence. Clearly mark test adapters/providers
  as test-only. Use synthetic/public data; never save keys, storage state or secrets.
- Update the file map, architecture and extension guide when moving interfaces
  or files. Check packaged JS/HTML resources when moving their implementation.
- Commit meaningful milestones. No public push, deployment or submission unless
  separately authorized. Do not spend model calls on ordinary refactor tests.
