import pytest

from waypoint.domain.artifact import Action, Target


def test_generic_policy_does_not_treat_arbitrary_click_as_readonly():
    from waypoint.surfaces.browser.policy import Policy

    policy = Policy.for_url("https://example.com/")
    action = Action(
        kind="click", target=Target(by="role", role="button", name="Delete part")
    )
    with pytest.raises(ValueError, match="consequential"):
        policy.check_action(action, {"label": "Delete part"})
    with pytest.raises(ValueError, match="origin"):
        policy.check_action(
            action, {"label": "Documentation", "href": "https://outside.example/"}
        )
    with pytest.raises(ValueError, match="unclassified"):
        policy.check_action(action, {"label": "Do something"})
    assert not policy.request_allowed("https://example.com/api", "POST", "fetch")


async def test_consequential_button_is_rejected_before_actual_click():
    from tests.support.catalog import CatalogServer
    from waypoint.surfaces.browser.session import Browser

    with CatalogServer() as app:
        async with Browser(app.url + "lookup?part=B-22") as surface:
            button = surface.page.get_by_role("button", name="Delete part")
            # Fixture setup, not an available discovery/replay tool.
            await button.evaluate(
                "e => e.onclick = () => e.setAttribute('data-clicked', 'yes')"
            )
            with pytest.raises(ValueError, match="consequential"):
                await surface.act(
                    Action(
                        kind="click",
                        target=Target(by="role", role="button", name="Delete part"),
                    ),
                    {},
                )
            assert await button.get_attribute("data-clicked") is None
