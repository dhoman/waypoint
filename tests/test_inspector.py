import json

from waypoint.inspector import render_inspector
from waypoint.schema import Capability


def test_inspector_embeds_real_artifact_and_run_without_executable_ui_text(tmp_path):
    artifact = Capability.model_validate_json(open("evidence/capability.json").read())
    run = tmp_path / "run"
    run.mkdir()
    (run / "events.jsonl").write_text(
        json.dumps(
            {
                "event": "recognition",
                "state": "s2",
                "observation": {"text": "</script><script>alert(1)</script>"},
            }
        )
        + "\n"
    )
    (run / "result.json").write_text(
        json.dumps(
            {"status": "awaiting_intervention", "state": "s2", "transition": "t2"}
        )
    )
    output = tmp_path / "inspector.html"
    render_inspector(artifact, [run], output)
    rendered = output.read_text()
    assert "member-invoice-summary" in rendered
    assert "awaiting_intervention" in rendered
    assert "</script><script>alert(1)" not in rendered
