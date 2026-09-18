# Documentation guide

There is one current implementation: generic workflow discovery and replay using
schema 2.0. Version 1 was retired; old run evidence is historical, not a second
engine you need to understand.

## Reading paths

| Your task | Read in this order |
|---|---|
| Run a workflow | [Root README](../README.md) → [evidence inventory](../evidence/README.md) |
| Understand the code | [Architecture](ARCHITECTURE.md) → [file/class map](../waypoint/README.md) |
| Add a surface | [Architecture](ARCHITECTURE.md) → [extension guide](EXTENDING.md) → [surface interface](../waypoint/surfaces/protocol.py) |
| Add a provider or vocabulary operation | [Extension guide](EXTENDING.md) → [contributor guide](../CONTRIBUTING.md) |
| Fix a failure | [Execution walkthrough](ARCHITECTURE.md#execution-walkthrough) → [test map](../tests/README.md) → the run's result/events/inspector |
| Review the take-home | [REPORT](../REPORT.md) → [evidence](../evidence/README.md) → [OpenAdapt ADR](adr-001-surface.md) |
| Work as an agent | [AGENTS.md](../AGENTS.md) → [contributor guide](../CONTRIBUTING.md) → relevant package/test map |

The README is operational; the architecture document explains relationships;
the package map owns the per-file inventory; the extension guide owns interface
invariants. Update the relevant document when changing its subject rather than
copying descriptions into several places. `REPORT.md` retains the assignment's
required headings and short evaluation narrative.

## Design history

[ADR 001](adr-001-surface.md) records the bounded OpenAdapt inspection and the
decision to own a direct async adapter. It is a historical decision record, not
a claim that a native adapter exists. [PLAN.md](../PLAN.md) records implementation
milestones; it is not the architecture reference.
