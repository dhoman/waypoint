"""Test-only specialization of saved schema-2 artifacts; never discovery evidence."""

from pathlib import Path
from urllib.parse import urlsplit

from waypoint.domain.artifact import Capability, Predicate, Screen, State
from waypoint.domain.base import Provenance


def member_capability(url, *, missing_branch=False):
    cap = Capability.model_validate_json(
        Path("evidence/web-member-discovery-6/capability.json").read_text()
    )
    parsed = urlsplit(url)
    cap.origin = f"{parsed.scheme}://{parsed.netloc}"
    cap.discovery_run, cap.provider, cap.model = "test-authored", "test", "none"
    if missing_branch:
        cap.screens["missing"] = Screen(
            id="missing",
            recognition=[Predicate(op="heading", value="No members found")],
            identity=[
                Predicate(op="field_equals_input", field="Search ID", input="memberId")
            ],
            provenance=Provenance(origin="authored", note="Test-only business branch"),
        )
        cap.states["missing"] = State(
            id="missing",
            screen="missing",
            progress="terminal",
            outcome="member_not_found",
        )
        cap.terminals.append("missing")
        cap.transitions[1].alternatives["missing"] = []
    return Capability.model_validate(cap.model_dump())
