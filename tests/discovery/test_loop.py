from tests.support.catalog import CatalogServer
from waypoint.surfaces.browser.session import Browser


async def test_discovery_compiles_against_surface_contract_without_browser_url(
    tmp_path,
):
    from tests.support.memory_surface import MemorySurface
    from waypoint.discovery.loop import discover
    from waypoint.discovery.models import Decision, ScreenProposal
    from waypoint.domain.artifact import (
        Action,
        Extraction,
        Observation,
        Predicate,
        Target,
    )
    from waypoint.evidence.trace import Trace

    action = Action(kind="click", target=Target(by="text", name="Open"))

    class Provider:
        name, model = "test-only", "none"

        async def decide(self, goal, inputs, observation, history):
            heading = observation.headings[0]
            return Decision(
                operation="click" if heading == "Home" else "finish",
                target=action.target if heading == "Home" else None,
                screen=ScreenProposal(
                    id=heading.lower(),
                    recognition=[Predicate(op="heading", value=heading)],
                ),
                outputs=[]
                if heading == "Home"
                else [
                    Extraction(
                        name="amount",
                        source="field",
                        field="Amount",
                        value_type="number",
                    )
                ],
                rationale="Test-only surface substitution",
            )

    async with MemorySurface(
        [
            Observation(headings=["Home"]),
            Observation(headings=["Details"], fields={"Amount": "19.75"}),
        ],
        [action],
    ) as surface:
        cap = await discover(
            "Read amount", surface, {}, Provider(), Trace(tmp_path, kind="test")
        )
    assert cap is not None
    assert cap.origin == "memory:test"
    assert len(cap.transitions) == 2


async def test_generic_discovery_validates_model_proposed_outputs(tmp_path):
    from waypoint.discovery.loop import discover
    from waypoint.discovery.models import Decision, ScreenProposal
    from waypoint.domain.artifact import Extraction, Predicate
    from waypoint.evidence.trace import Trace

    class Provider:
        name = "test"
        model = "fabricated"

        async def decide(self, goal, inputs, observation, history):
            return Decision(
                operation="finish",
                screen=ScreenProposal(
                    id="catalog",
                    recognition=[Predicate(op="heading", value="Workshop catalog")],
                ),
                outputs=[Extraction(name="price", source="field", field="nonexistent")],
                rationale="A test-only invalid output rule",
            )

    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            cap = await discover(
                "Read a price", browser, {}, Provider(), Trace(tmp_path, kind="test")
            )
    assert cap is None
    assert not (tmp_path / "capability.json").exists()
    assert "output field missing" in (tmp_path / "events.jsonl").read_text()
    assert "no_progress" in (tmp_path / "result.json").read_text()
