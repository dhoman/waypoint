"""A package refactor must not invalidate the fingerprints of saved v2 runs."""

import hashlib
import json
from pathlib import Path

import pytest

from waypoint.domain.artifact import Capability


@pytest.mark.parametrize(
    "artifact,run",
    [
        ("web-books-discovery-5", "web-books-replay-5"),
        ("web-member-discovery-6", "web-member-replay"),
    ],
)
def test_retained_artifact_keeps_its_canonical_digest(artifact, run):
    cap = Capability.model_validate_json(
        Path(f"evidence/{artifact}/capability.json").read_text()
    )
    first_event = json.loads(
        Path(f"evidence/{run}/events.jsonl").read_text().splitlines()[0]
    )
    assert (
        hashlib.sha256(cap.model_dump_json().encode()).hexdigest()
        == first_event["artifact_sha256"]
    )
