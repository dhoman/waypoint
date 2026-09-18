from waypoint.browser import BrowserSurface
from waypoint.discovery import Decision, discover
from waypoint.evidence import Trace
from waypoint.fixture import FixtureServer
from waypoint.schema import Inputs


class RepeatingProvider:
    name = "fabricated-test-provider"
    model = "none"

    async def decide(self, *args):
        return Decision(
            operation="wait", target=None, input=None, rationale="test no progress"
        )


async def test_discovery_stops_repeated_no_progress(tmp_path):
    with FixtureServer() as app:
        async with BrowserSurface(app.url) as browser:
            result = await discover(
                "Invoice summary",
                browser,
                Inputs(memberId="M-101"),
                RepeatingProvider(),
                Trace(tmp_path, kind="fabricated-test"),
                max_steps=10,
            )
    assert result is None
    assert '"failure_category": "no_progress"' in (tmp_path / "result.json").read_text()
