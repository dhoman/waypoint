import pytest

from tests.support.catalog import CatalogServer
from waypoint.domain.artifact import Action, Target
from waypoint.surfaces.browser.session import Browser


async def test_generic_compiled_extraction_replays_new_input(tmp_path):
    from waypoint.discovery.compiler import compile_route
    from waypoint.domain.artifact import Extraction, Predicate, Screen
    from waypoint.evidence.trace import Trace
    from waypoint.runtime.replay import Replay

    inputs = {"part": "A-11"}
    search = Screen(
        id="catalog", recognition=[Predicate(op="heading", value="Workshop catalog")]
    )
    details = Screen(
        id="details",
        recognition=[Predicate(op="heading", value="Part details")],
        identity=[
            Predicate(op="field_equals_input", field="Part number", input="part")
        ],
    )
    actions = [
        Action(
            kind="fill", target=Target(by="label", name="Part number"), input="part"
        ),
        Action(
            kind="click", target=Target(by="role", role="button", name="Search parts")
        ),
    ]
    output = [
        Extraction(name="part", source="field", field="Part number"),
        Extraction(name="price", source="field", field="Price", value_type="number"),
    ]
    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            observations = [await browser.observe()]
            for action in actions:
                await browser.act(action, inputs)
                observations.append(await browser.observe())
        cap = compile_route(
            observations,
            actions,
            [search, search, details],
            output,
            inputs=inputs,
            goal="Find a part and read its price",
            binding=browser.binding,
            run_id="test",
            provider="test",
            model="none",
        )
        async with Browser(app.url) as browser:
            result = await Replay(
                cap, browser, {"part": "B-22"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "succeeded"
    assert result.outputs == {"part": "B-22", "price": 19.75}


async def test_generic_handoff_revalidates_same_page_and_captures_manual_event(
    tmp_path,
):
    """Simulated operator test, not evidence of a physical human interaction."""
    from waypoint.discovery.compiler import compile_route
    from waypoint.domain.artifact import Extraction, Predicate, Screen
    from waypoint.evidence.trace import Trace
    from waypoint.runtime.replay import Replay

    with CatalogServer() as app:
        async with Browser(app.url + "lookup?part=B-22") as browser:
            inputs = {"part": "B-22"}
            screen = Screen(
                id="details",
                recognition=[Predicate(op="heading", value="Part details")],
                identity=[
                    Predicate(
                        op="field_equals_input", field="Part number", input="part"
                    )
                ],
            )
            cap = compile_route(
                [await browser.observe()],
                [],
                [screen],
                [
                    Extraction(
                        name="price", source="field", field="Price", value_type="number"
                    )
                ],
                inputs=inputs,
                goal="Read part price",
                binding=browser.binding,
                run_id="test",
                provider="test",
                model="none",
            )
            # Test-only fixture manipulation; never available to the discovery model.
            await browser.page.evaluate("""() => {
              const d=document.createElement('dialog'); d.open=true;
              const b=document.createElement('button'); b.textContent='Dismiss notice';
              b.onclick=()=>d.remove(); d.append(b); document.body.append(d);
            }""")
            page = browser.page
            runner = Replay(cap, browser, inputs, Trace(tmp_path, cap, kind="test"))
            assert (await runner.run()).status == "awaiting_intervention"
            token = browser.ownership.token
            runner.take_control(token)
            with pytest.raises(ValueError, match="ownership"):
                await browser.act(
                    Action(
                        kind="click", target=Target(by="text", name="Dismiss notice")
                    ),
                    inputs,
                )
            assert not await runner.resume(token)
            await page.get_by_role("button", name="Dismiss notice").click()
            assert await runner.resume(token)
            assert browser.page is page
            with pytest.raises(ValueError, match="stale"):
                await runner.resume(token)
            assert (await runner.run()).outputs == {"price": 19.75}
    events = (tmp_path / "events.jsonl").read_text()
    assert '"event": "human_action"' in events
    assert '"event": "resume_rejected"' in events
