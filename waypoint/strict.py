"""Executable replay isolation proof, not a self-reported model call counter.

Python imports and outbound sockets are blocked; Chromium separately enforces
the runtime origin/route allowlist. This is defense in depth, not an OS sandbox.
"""

import importlib.abc
import json
import os
import socket
import sys
from pathlib import Path


class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {
            "openai",
            "anthropic",
            "httpx",
            "requests",
        } or fullname in {"waypoint.provider", "waypoint.discovery"}:
            raise ImportError("Strict replay blocks model dependencies")
        return None


def audit(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address[0] not in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            raise PermissionError("Strict replay blocks non-loopback connections")


def install():
    for key in list(os.environ):
        if key.endswith("API_KEY") or key in {
            "OPENAI_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN",
        }:
            os.environ.pop(key, None)
    sys.meta_path.insert(0, NoModels())
    sys.addaudithook(audit)


def proof():
    checks = {}
    try:
        __import__("waypoint.provider")
    except ImportError:
        checks["provider_import"] = "blocked"
    try:
        with socket.socket() as probe:
            probe.connect(("203.0.113.1", 443))
    except PermissionError:
        checks["external_connection"] = "blocked"
    if len(checks) != 2:
        raise RuntimeError("Strict isolation self-test failed")
    return checks


def main():
    install()
    checks = proof()
    print(json.dumps({"strict_replay": checks}), flush=True)
    if sys.argv[1:] == ["--self-test"]:
        return
    if len(sys.argv) < 2 or sys.argv[1] != "replay":
        raise SystemExit("Strict entrypoint accepts only replay")
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        with (out / "isolation.json").open("x") as f:
            json.dump(
                {
                    "checks": checks,
                    "api_credentials_removed": True,
                    "browser_network": "separate runtime origin/route allowlist",
                    "scope": "Python process guard, not OS-level sandbox",
                },
                f,
                indent=2,
            )
    from waypoint.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
