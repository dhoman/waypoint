from tests.support.memory_surface import MemorySurface
from waypoint.domain.artifact import (
    Action,
    Capability,
    Extraction,
    Observation,
    Predicate,
    Screen,
    State,
    Target,
    Transition,
)
from waypoint.evidence.trace import Trace
from waypoint.runtime.replay import Replay


async def test_replay_uses_surface_contract_without_browser_objects_or_url(tmp_path):
    action = Action(kind="click", target=Target(by="text", name="Open"))
    cap = Capability(
        capability_id="test-only",
        description="Read displayed amount",
        app="Test",
        origin="memory:test",
        entry_path="/",
        required_inputs={},
        output=[
            Extraction(
                name="amount", source="field", field="Amount", value_type="number"
            )
        ],
        entry="start",
        screens={
            "home": Screen(
                id="home", recognition=[Predicate(op="heading", value="Home")]
            ),
            "details": Screen(
                id="details", recognition=[Predicate(op="heading", value="Details")]
            ),
        },
        states={
            "start": State(id="start", screen="home", progress="ready"),
            "read": State(
                id="read", screen="details", progress="selected", checkpoint=True
            ),
            "done": State(id="done", progress="terminal", outcome="succeeded"),
        },
        transitions=[
            Transition(id="open", source="start", destination="read", action=action),
            Transition(
                id="extract",
                source="read",
                destination="done",
                action=Action(kind="extract"),
            ),
        ],
        terminals=["done"],
        discovery_run="test-only",
        provider="test",
        model="none",
    )
    async with MemorySurface(
        [
            Observation(headings=["Home"]),
            Observation(headings=["Details"], fields={"Amount": "19.75"}),
        ],
        [action],
    ) as surface:
        result = await Replay(cap, surface, {}, Trace(tmp_path, cap)).run()
    assert result.status == "succeeded"
    assert result.outputs == {"amount": 19.75}
    assert surface.closed
