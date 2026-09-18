from waypoint.browser import BrowserSurface
from waypoint.compiler import amend_missing_member, compile_route
from waypoint.engine import Replay
from waypoint.evidence import Trace
from waypoint.fixture import FixtureServer
from waypoint.schema import Action, Inputs, Target

# Explicitly authored test route; never presented as LLM discovery evidence.
TEST_ACTIONS = [
    Action(kind="fill", target=Target(by="label", name="Member ID"), input="memberId"),
    Action(kind="click", target=Target(by="role", name="Search")),
    Action(
        kind="click",
        target=Target(
            by="role", role="link", name="View profile", row_input="memberId"
        ),
    ),
    Action(kind="click", target=Target(by="role", role="link", name="Invoices")),
]


async def recorded_test_capability(url):
    steps = []
    async with BrowserSurface(url) as browser:
        for action in TEST_ACTIONS:
            before = await browser.observe()
            await browser.act(action, Inputs(memberId="M-101"))
            steps.append((before, action, await browser.observe()))
    return amend_missing_member(
        compile_route(
            steps,
            run_id="test-authored",
            provider="test",
            model="none",
            goal="Invoice summary",
        )
    )


async def test_compiled_route_replays_for_other_member_without_provider(tmp_path):
    with FixtureServer() as app:
        cap = await recorded_test_capability(app.url)
        async with BrowserSurface(app.url) as browser:
            result = await Replay(
                cap, browser, Inputs(memberId="M-202"), Trace(tmp_path, cap)
            ).run()
    assert result.status == "succeeded"
    assert result.outputs.memberId == "M-202"
    assert result.outputs.total == 100.0
    assert [i.invoice_id for i in result.outputs.invoices] == ["INV-2021", "INV-2022"]


async def test_missing_member_is_declared_business_outcome(tmp_path):
    with FixtureServer() as app:
        cap = await recorded_test_capability(app.url)
        async with BrowserSurface(app.url) as browser:
            result = await Replay(
                cap, browser, Inputs(memberId="M-999"), Trace(tmp_path, cap)
            ).run()
    assert result.status == "business_outcome"
    assert result.business_code == "member_not_found"
