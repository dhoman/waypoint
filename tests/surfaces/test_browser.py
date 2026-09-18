from tests.support.catalog import CatalogServer
from waypoint.domain.artifact import Action, Target
from waypoint.surfaces.browser.session import Browser


async def test_unrelated_top_level_site_accepts_arbitrary_input_without_site_code():
    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            obs = await browser.observe()
            assert "Workshop catalog" in obs.headings
            await browser.act(
                Action(
                    kind="fill",
                    target=Target(by="label", name="Part number"),
                    input="part",
                ),
                {"part": "B-22"},
            )
            await browser.act(
                Action(
                    kind="click",
                    target=Target(by="role", role="button", name="Search parts"),
                ),
                {"part": "B-22"},
            )
            observed = await browser.observe()
            assert observed.fields == {"Part number": "B-22", "Price": "19.75"}


async def test_generic_adapter_synchronizes_iframe_navigation():
    from waypoint.demo.member_console import FixtureServer

    with FixtureServer() as app:
        async with Browser(app.url) as browser:
            inputs = {"entity": "M-202"}
            for kind, target, binding in [
                (
                    "fill",
                    Target(by="label", name="Member ID", frame="Member workspace"),
                    "entity",
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="button",
                        name="Search",
                        frame="Member workspace",
                    ),
                    None,
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="link",
                        name="View profile",
                        row_input="entity",
                        frame="Member workspace",
                    ),
                    None,
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="link",
                        name="Invoices",
                        frame="Member workspace",
                    ),
                    None,
                ),
            ]:
                await browser.act(
                    Action(kind=kind, target=target, input=binding), inputs
                )
            observed = await browser.observe()
            assert "Member invoices" in observed.headings
            assert observed.fields["Member ID"] == "M-202"
