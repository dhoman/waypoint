import pytest

from tests.support.artifacts import member_capability
from waypoint.demo.member_console import FixtureServer
from waypoint.evidence.trace import Trace
from waypoint.runtime.replay import Replay
from waypoint.surfaces.browser.session import Browser


async def test_compiled_route_replays_for_other_member_without_provider(tmp_path):
    with FixtureServer() as app:
        cap = member_capability(app.url, missing_branch=True)
        async with Browser(app.url) as browser:
            result = await Replay(
                cap, browser, {"memberId": "M-202"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "succeeded"
    assert result.outputs["member_id"] == "M-202"
    assert result.outputs["total_amount_usd"] == 100.0
    assert [i["invoice"] for i in result.outputs["invoice_rows"]] == [
        "INV-2021",
        "INV-2022",
    ]


async def test_missing_member_is_declared_business_outcome(tmp_path):
    with FixtureServer() as app:
        cap = member_capability(app.url, missing_branch=True)
        async with Browser(app.url) as browser:
            result = await Replay(
                cap, browser, {"memberId": "M-999"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "business_outcome"
    assert result.business_code == "member_not_found"


@pytest.mark.parametrize(
    "scenario,category", [("mismatch", "identity"), ("ambiguous", "ambiguity")]
)
async def test_wrong_identity_or_ambiguous_target_stops_before_invoices(
    tmp_path, scenario, category
):
    with FixtureServer() as app:
        cap = member_capability(app.url, missing_branch=True)
        async with Browser(app.url + "?scenario=" + scenario) as browser:
            result = await Replay(
                cap, browser, {"memberId": "M-202"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "failed"
    assert result.failure_category == category
    assert '"transition": "t3"' not in (tmp_path / "events.jsonl").read_text()
    assert any(e.endswith(".png") for e in result.evidence)


async def test_slow_ui_waits_for_declared_loading_condition(tmp_path):
    with FixtureServer() as app:
        cap = member_capability(app.url, missing_branch=True)
        async with Browser(app.url + "?scenario=slow") as browser:
            result = await Replay(
                cap, browser, {"memberId": "M-202"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "succeeded"
    assert result.outputs["total_amount_usd"] == 100
    assert '"timing": "application_wait"' in (tmp_path / "events.jsonl").read_text()


async def test_handoff_blocks_actions_and_rejects_resume_while_dialog_remains(tmp_path):
    with FixtureServer() as app:
        cap = member_capability(app.url, missing_branch=True)
        async with Browser(app.url + "?scenario=dialog") as browser:
            runner = Replay(cap, browser, {"memberId": "M-202"}, Trace(tmp_path, cap))
            result = await runner.run()
            assert result.status == "awaiting_intervention"
            token = browser.ownership.token
            runner.take_control(token)
            with pytest.raises(ValueError, match="ownership"):
                await browser.act(cap.transitions[3].action, {"memberId": "M-202"})
            assert not await runner.resume(token)
            assert browser.ownership.state == "human"
            assert runner.cancel().status == "cancelled"
