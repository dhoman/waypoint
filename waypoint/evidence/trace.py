"""Synthetic-only evidence boundary. Never persist provider prompts or secrets."""

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from waypoint.domain.artifact import Observation


def sanitized(obs: Observation):
    data = obs.model_dump()
    data["fields"] = {
        k: v for k, v in data["fields"].items() if not k.startswith("input:")
    }
    # Fixture text is synthetic, but input values are never kept in snapshots.
    return data


def sanitize_manual_event(event):
    return {
        "kind": event["kind"],
        "tag": str(event.get("tag", ""))[:20],
        "target": str(event.get("target", ""))[:100],
        "value": "[redacted]" if event["kind"] == "input" else None,
    }


class Trace:
    def __init__(self, directory, capability=None, *, kind="replay"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        if (self.directory / "events.jsonl").exists():
            raise ValueError("refusing to overwrite existing run evidence")
        self.run_id = self.directory.name + "-" + uuid.uuid4().hex[:8]
        self.capability = capability
        self.sequence = 0
        self.start = time.monotonic()
        self.emit(
            "run_started",
            kind=kind,
            code_version="0.1.0",
            source_sha256=source_digest(),
            artifact_sha256=hashlib.sha256(
                capability.model_dump_json().encode()
            ).hexdigest()
            if capability
            else None,
        )

    def emit(self, event, **data):
        self.sequence += 1
        record = dict(
            seq=self.sequence,
            run_id=self.run_id,
            capability_id=self.capability.capability_id
            if self.capability
            else "discovery",
            revision=self.capability.revision if self.capability else None,
            at=datetime.now(UTC).isoformat(),
            elapsed_s=round(time.monotonic() - self.start, 4),
            event=event,
            **data,
        )
        with (self.directory / "events.jsonl").open("a") as f:
            f.write(json.dumps(record) + "\n")

    def save(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value, indent=2) + "\n")
        return name


def source_digest():
    digest = hashlib.sha256()
    root = Path(__file__).parents[1]
    for path in sorted(root.rglob("*")):
        if path.suffix in {".py", ".html", ".js"}:
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()
