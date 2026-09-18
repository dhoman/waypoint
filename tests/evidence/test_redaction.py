from waypoint.evidence.trace import sanitize_manual_event


def test_manual_input_evidence_cannot_retain_typed_values():
    captured = sanitize_manual_event(
        {
            "kind": "input",
            "tag": "INPUT",
            "target": "Operator note",
            "value": "secret typed content",
            "unapproved": "another secret",
        }
    )
    assert captured == {
        "kind": "input",
        "tag": "INPUT",
        "target": "Operator note",
        "value": "[redacted]",
    }
