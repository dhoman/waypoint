def test_discovery_separates_entity_predicate_from_screen_type():
    from waypoint.discovery.loop import parameterize
    from waypoint.discovery.models import Decision, ScreenProposal
    from waypoint.domain.artifact import Observation, Predicate

    binding = Predicate(op="field_equals_input", field="Account", input="account")
    decision = Decision(
        operation="wait",
        rationale="test",
        screen=ScreenProposal(
            id="details",
            recognition=[Predicate(op="heading", value="Details"), binding],
        ),
    )
    screen = parameterize(
        decision,
        Observation(headings=["Details"], fields={"Account": "A"}),
        {"account": "A"},
    )
    assert screen.recognition == [Predicate(op="heading", value="Details")]
    assert screen.identity == [binding]
