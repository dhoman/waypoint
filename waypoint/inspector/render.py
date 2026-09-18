"""Standalone, offline graph inspector generated solely from artifact/run data."""

import base64
import json
from pathlib import Path

from waypoint.domain.artifact import Capability


def render_inspector(capability: Capability, run_dirs: list[Path], output: Path):
    runs = []
    for directory in run_dirs:
        events = [
            json.loads(line)
            for line in (directory / "events.jsonl").read_text().splitlines()
            if line
        ]
        result = json.loads((directory / "result.json").read_text())
        evidence = {}
        for event in events:
            for name in event.get("evidence", []):
                path = (directory / name).resolve()
                if not path.is_relative_to(directory.resolve()) or not path.is_file():
                    continue
                if path.suffix == ".png":
                    evidence[name] = (
                        "data:image/png;base64,"
                        + base64.b64encode(path.read_bytes()).decode()
                    )
                elif path.suffix == ".json":
                    evidence[name] = json.loads(path.read_text())
        runs.append(
            {
                "name": directory.name,
                "events": events,
                "result": result,
                "evidence": evidence,
            }
        )
    data = (
        json.dumps({"artifact": capability.model_dump(), "runs": runs})
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    template = Path(__file__).with_name("template.html").read_text()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__WAYPOINT_DATA__", data))
