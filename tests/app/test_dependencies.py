"""Dependency rules protect strict replay and offline inspection during extension."""

import ast
import subprocess
import sys
from pathlib import Path


def test_cli_loading_does_not_start_browser_or_load_model_dependencies():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import waypoint.app.cli
for prefix in ('playwright', 'openai', 'waypoint.providers', 'waypoint.discovery'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
""",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_engine_layers_do_not_import_concrete_adapters_or_application_wiring():
    allowed = {
        "domain": ("waypoint.domain",),
        "runtime": (
            "waypoint.domain",
            "waypoint.runtime",
            "waypoint.evidence",
            "waypoint.surfaces.protocol",
        ),
        "discovery": (
            "waypoint.domain",
            "waypoint.discovery",
            "waypoint.runtime.interpret",
            "waypoint.evidence",
            "waypoint.surfaces.protocol",
        ),
        "evidence": ("waypoint.domain", "waypoint.evidence"),
        "inspector": ("waypoint.domain", "waypoint.inspector"),
        "providers": (),
    }
    for layer, prefixes in allowed.items():
        for path in Path("waypoint", layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                imports = (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                for name in imports:
                    if name.startswith("waypoint."):
                        assert any(
                            name == prefix or name.startswith(prefix + ".")
                            for prefix in prefixes
                        ), f"{path}: forbidden dependency {name}"
