import json
from pathlib import Path

import pytest

from waypoint.domain.artifact import Capability
from waypoint.evidence.qualification import qualify


def test_validation_requires_matching_artifact_and_terminal_coverage(tmp_path):
    cap = Capability.model_validate_json(
        Path("evidence/web-books-discovery-5/capability.json").read_text()
    )
    with pytest.raises(ValueError, match="coverage"):
        qualify(cap, [])
    qualified = qualify(cap, [Path("evidence/web-books-replay-5")])
    assert qualified.status == "validated"
    assert all(t.provenance.validated for t in qualified.transitions)
    assert cap.status == "draft"
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    (tampered / "result.json").write_text(
        Path("evidence/web-books-replay-5/result.json").read_text()
    )
    events = [
        json.loads(s)
        for s in Path("evidence/web-books-replay-5/events.jsonl")
        .read_text()
        .splitlines()
    ]
    events[0]["artifact_sha256"] = "wrong"
    (tampered / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="artifact"):
        qualify(cap, [tampered, Path("evidence/web-books-missing")])
