"""Local evidence annotation, not an approval service or reliability claim."""

import hashlib
import json

from waypoint.domain.artifact import Capability


def qualify(cap: Capability, run_dirs):
    digest = hashlib.sha256(cap.model_dump_json().encode()).hexdigest()
    terminals, transitions, screens, destinations = set(), set(), set(), set()
    evidence = []
    for directory in run_dirs:
        events = [
            json.loads(line)
            for line in (directory / "events.jsonl").read_text().splitlines()
        ]
        result = json.loads((directory / "result.json").read_text())
        if not events or events[0].get("artifact_sha256") != digest:
            raise ValueError("validation evidence belongs to a different artifact")
        if result["status"] not in {"succeeded", "business_outcome"}:
            continue
        terminals.add(result["state"])
        transitions.update(
            e["transition"] for e in events if e["event"] == "transition_completed"
        )
        destinations.update(
            e["state"] for e in events if e["event"] == "transition_completed"
        )
        screens.update(
            e["screen"]
            for e in events
            if e["event"] == "recognition" and e["kind"] == "recognized"
        )
        evidence.append(f"{directory.name}/events.jsonl")
    required_destinations = {t.destination for t in cap.transitions} | {
        dest for t in cap.transitions for dest in t.alternatives
    }
    if (
        not set(cap.terminals) <= terminals
        or not {t.id for t in cap.transitions} <= transitions
        or not required_destinations <= destinations
    ):
        raise ValueError(
            "validation coverage incomplete: every terminal, edge and alternative needs execution evidence"
        )
    qualified = cap.model_copy(deep=True)
    qualified.status = "validated"
    qualified.validation_evidence = evidence
    for t in qualified.transitions:
        t.provenance.validated = t.id in transitions
        t.provenance.evidence.extend(evidence)
    for s in qualified.screens.values():
        s.provenance.validated = s.id in screens
        s.provenance.evidence.extend(evidence)
    return type(cap).model_validate(qualified.model_dump())
