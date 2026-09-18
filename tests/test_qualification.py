import json
from pathlib import Path

import pytest

from waypoint.qualification import qualify
from waypoint.schema import Capability


def test_validation_requires_matching_artifact_and_terminal_coverage(tmp_path):
    cap = Capability.model_validate_json(Path("evidence/capability.json").read_text())
    with pytest.raises(ValueError, match="coverage"):
        qualify(cap, [Path("evidence/replay-b")])
    qualified = qualify(
        cap, [Path("evidence/replay-b"), Path("evidence/missing-member")]
    )
    assert qualified.status == "validated"
    assert all(t.provenance.validated for t in qualified.transitions)
    assert cap.status == "draft"
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    (tampered / "result.json").write_text(
        Path("evidence/replay-b/result.json").read_text()
    )
    events = [
        json.loads(s)
        for s in Path("evidence/replay-b/events.jsonl").read_text().splitlines()
    ]
    events[0]["artifact_sha256"] = "wrong"
    (tampered / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="artifact"):
        qualify(cap, [tampered, Path("evidence/missing-member")])
