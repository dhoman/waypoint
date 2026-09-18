import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from waypoint.domain.artifact import Capability, Observation
from waypoint.evidence.trace import Trace
from waypoint.runtime.replay import Replay
from waypoint.surfaces.browser.session import Browser


def artifact():
    return json.loads(
        Path("evidence/web-member-discovery-6/capability.json").read_text()
    )


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
        data["transitions"] = [t for t in data["transitions"] if t["id"] != "t4"]
    elif damage == "unbounded":
        data["max_steps"] = 0
    elif damage == "action":
        data["transitions"][0]["action"]["kind"] = "eval"
    elif damage == "locator":
        data["transitions"][0]["action"]["target"]["kind"] = "windows_uia"
    elif damage == "retry":
        data["transitions"][0]["retries"] = 1
    with pytest.raises(ValidationError):
        Capability.model_validate(data)


def test_missing_input_never_defaults_to_discovery_member():
    with pytest.raises(ValueError, match="required inputs"):
        Capability.model_validate(artifact()).validate_inputs({})


async def test_multiple_matching_transition_guards_are_an_error(tmp_path):
    cap = Capability.model_validate(artifact())
    duplicate = cap.transitions[0].model_copy(update={"id": "duplicate"})
    cap.transitions.append(duplicate)
    runner = Replay(
        cap,
        Browser(cap.origin + cap.entry_path),
        {"memberId": "M-202"},
        Trace(tmp_path, cap),
    )
    runner.obs = Observation()
    with pytest.raises(ValueError, match="ambiguous transitions"):
        await runner.choose(cap.entry)
