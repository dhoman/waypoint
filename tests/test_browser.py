import pytest

from waypoint.browser import BrowserSurface
from waypoint.fixture import FixtureServer
from waypoint.schema import Action, Inputs, Target


@pytest.mark.asyncio
async def test_ui_route_reads_requested_members_actual_invoice_data():
    with FixtureServer() as app:
        async with BrowserSurface(app.url) as browser:
            inputs = Inputs(memberId="M-202")
            await browser.act(
                Action(
                    kind="fill",
                    target=Target(by="label", name="Member ID"),
                    input="memberId",
                ),
                inputs,
            )
            await browser.act(
                Action(
                    kind="click", target=Target(by="role", role="button", name="Search")
                ),
                inputs,
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
            assert (await browser.observe()).fields["Member ID"] == "M-202"
            await browser.act(
                Action(
                    kind="click", target=Target(by="role", role="link", name="Invoices")
                ),
                inputs,
            )
            observed = await browser.observe()
            assert observed.fields["Member ID"] == "M-202"
            assert observed.tables[0]["rows"] == [
                ["INV-2021", "84.25", "Open"],
                ["INV-2022", "15.75", "Paid"],
            ]
