import pytest

from waypoint.browser import BrowserSurface
from waypoint.fixture import FixtureServer
from waypoint.schema import Action, Inputs, Target


async def test_consequential_control_is_rejected_before_click():
    with FixtureServer() as app:
        async with BrowserSurface(app.url + "?scenario=normal") as browser:
            inputs = Inputs(memberId="M-101")
            await browser.act(
                Action(
                    kind="fill",
                    target=Target(by="label", name="Member ID"),
                    input="memberId",
                ),
                inputs,
            )
            await browser.act(
                Action(kind="click", target=Target(by="role", name="Search")), inputs
            )
            await browser.act(
                Action(
                    kind="click",
                    target=Target(
                        by="role",
                        role="link",
                        name="View profile",
                        row_input="memberId",
                    ),
                ),
                inputs,
            )
            with pytest.raises(ValueError, match="policy"):
                await browser.act(
                    Action(
                        kind="click", target=Target(by="role", name="Close account")
                    ),
                    inputs,
                )
            assert "Account closed" not in (await browser.observe()).text
