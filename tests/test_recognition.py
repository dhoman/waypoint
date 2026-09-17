import pytest

from waypoint.recognition import recognize
from waypoint.schema import Inputs, Observation, Predicate, Provenance, Screen


def profile():
    return Screen(
        id="profile",
        recognition=[Predicate(op="heading", value="Member profile")],
        identity=Predicate(
            op="field_equals_input", field="Member ID", input="memberId"
        ),
        provenance=Provenance(origin="authored", note="Test fixture"),
    )


def test_shared_screen_template_does_not_erase_wrong_entity_check():
    screen = profile()
    obs = Observation(
        headings=["Member profile"], fields={"Member ID": "M-101"}, version="1.0"
    )
    accepted = recognize({"profile": screen}, obs, Inputs(memberId="M-101"))
    assert accepted.kind == "recognized" and accepted.screen == "profile"
    with pytest.raises(ValueError, match="identity"):
        recognize({"profile": screen}, obs, Inputs(memberId="M-202"))


def test_ambiguous_screen_is_not_selected_by_catalog_order():
    obs = Observation(
        headings=["Member profile"], fields={"Member ID": "M-101"}, version="1.0"
    )
    assert (
        recognize({"a": profile(), "b": profile()}, obs, Inputs(memberId="M-101")).kind
        == "ambiguous"
    )
