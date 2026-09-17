"""Screen recognition and entity binding are deliberately separate decisions."""

from dataclasses import dataclass, field

from waypoint.schema import Inputs, Observation, Predicate, Screen


def holds(p: Predicate, obs: Observation, inputs: Inputs) -> bool:
    match p.op:
        case "heading":
            return p.value in obs.headings
        case "field_equals_input":
            return obs.fields.get(p.field) == getattr(inputs, p.input or "memberId")
        case "field_equals":
            return obs.fields.get(p.field) == p.value
        case "input_value":
            return obs.fields.get("input:" + p.field) == getattr(
                inputs, p.input or "memberId"
            )
        case "table_present":
            return sum(t["caption"] == p.value for t in obs.tables) == 1
        case "no_dialog":
            return not obs.dialog
    raise ValueError("unsupported predicate")


@dataclass
class Recognition:
    kind: str
    screen: str | None = None
    checks: dict = field(default_factory=dict)


def recognize(
    screens: dict[str, Screen], obs: Observation, inputs: Inputs
) -> Recognition:
    if obs.version != "1.0":
        return Recognition("unknown", checks={"version": "unsupported"})
    # Check visible identity even beneath a blocking overlay, before handoff.
    for key in ("Member ID", "Search ID"):
        if key in obs.fields and obs.fields[key] != inputs.memberId:
            raise ValueError(f"identity mismatch: {key}")
    if obs.dialog or obs.readonly:
        return Recognition(
            "unknown", checks={"blocking": "dialog" if obs.dialog else "read-only"}
        )
    if obs.loading:
        return Recognition("transient", checks={"loading": True})
    checks = {
        key: [holds(p, obs, inputs) for p in s.recognition]
        for key, s in screens.items()
    }
    matches = [key for key, passed in checks.items() if all(passed)]
    if len(matches) > 1:
        return Recognition("ambiguous", checks=checks)
    if not matches:
        return Recognition("unknown", checks=checks)
    key = matches[0]
    identity = screens[key].identity
    if identity and not holds(identity, obs, inputs):
        raise ValueError("identity binding not established")
    return Recognition("recognized", key, checks)
