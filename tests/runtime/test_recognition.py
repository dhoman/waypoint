import pytest


async def test_unknown_model_predicate_binding_is_rejected_before_browser_access():
    from waypoint.domain.artifact import Observation, Predicate
    from waypoint.runtime.interpret import holds

    with pytest.raises(ValueError, match="unknown predicate input"):
        await holds(
            Predicate(op="heading_input", input="invented"), Observation(), {}, None
        )


async def test_generic_identity_and_ambiguous_recognition_fail_closed():
    from waypoint.domain.artifact import Observation, Predicate, Screen
    from waypoint.runtime.interpret import recognize

    screen = Screen(
        id="details",
        recognition=[Predicate(op="heading", value="Details")],
        identity=[Predicate(op="field_equals_input", field="Account", input="account")],
    )
    obs = Observation(headings=["Details"], fields={"Account": "wrong"})
    with pytest.raises(ValueError, match="identity"):
        await recognize({"details": screen}, obs, {"account": "wanted"}, None)
    obs.fields["Account"] = "wanted"
    kind, _, _ = await recognize(
        {"one": screen, "two": screen}, obs, {"account": "wanted"}, None
    )
    assert kind == "ambiguous"
