import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from waypoint.engine import choose_transition
from waypoint.schema import Capability, Inputs, Observation


def artifact():
    return json.loads(Path("evidence/capability.json").read_text())


@pytest.mark.parametrize(
    "damage",
    ["target", "parameter", "unreachable", "unbounded", "action", "locator", "retry"],
)
def test_unsafe_or_malformed_artifacts_are_rejected(damage):
    data = artifact()
    if damage == "target":
        data["transitions"][0]["destination"] = "absent"
    elif damage == "parameter":
        data["transitions"][0]["action"]["input"] = "demonstratedIdentity"
    elif damage == "unreachable":
        data["transitions"] = [t for t in data["transitions"] if t["id"] != "extract"]
    elif damage == "unbounded":
        data["max_visits"] = 0
    elif damage == "action":
        data["transitions"][0]["action"]["kind"] = "eval"
    elif damage == "locator":
        data["transitions"][0]["action"]["target"]["kind"] = "windows_uia"
    elif damage == "retry":
        data["transitions"][0]["retries"] = 1
        data["transitions"][0]["retry_safe"] = True
    with pytest.raises(ValidationError):
        Capability.model_validate(data)


def test_missing_input_never_defaults_to_discovery_member():
    with pytest.raises(ValidationError):
        Inputs.model_validate({})


def test_multiple_matching_transition_guards_are_an_error():
    cap = Capability.model_validate(artifact())
    duplicate = cap.transitions[0].model_copy(update={"id": "duplicate"})
    cap.transitions.append(duplicate)
    with pytest.raises(ValueError, match="ambiguous transitions"):
        choose_transition(
            cap, cap.entry, Observation(version="1.0"), Inputs(memberId="M-202")
        )
