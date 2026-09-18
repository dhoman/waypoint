"""Command parsing and top-level dispatch. Concrete dependencies are wired here."""

import argparse
import asyncio
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Discover once; replay without a model"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixture")
    fixture.add_argument("--port", type=int, default=8765)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--artifact", required=True)
    inspect.add_argument("--runs", nargs="+", required=True)
    inspect.add_argument("--out", default="runs/inspector.html")
    validation = commands.add_parser("qualify")
    validation.add_argument("--artifact", required=True)
    validation.add_argument("--runs", nargs="+", required=True)
    validation.add_argument("--out", required=True)
    for command in ("discover", "replay"):
        p = commands.add_parser(command)
        p.add_argument("--url")
        p.add_argument("--input", action="append", default=[], metavar="NAME=VALUE")
        p.add_argument("--allow-origin", action="append", default=[])
        p.add_argument("--allow-control", action="append", default=[])
        p.add_argument("--allow-method", action="append", default=[])
        p.add_argument(
            "--prepare",
            action="store_true",
            help="Manually prepare/login to the same headed session",
        )
        p.add_argument("--out", required=True)
        p.add_argument("--headed", action="store_true")
        if command == "discover":
            p.add_argument(
                "--goal",
                default=None,
            )
            p.add_argument("--model", default=os.environ.get("WAYPOINT_MODEL"))
            p.add_argument("--max-steps", type=int, default=30)
            p.add_argument("--timeout", type=float, default=240)
        else:
            p.add_argument("--artifact", required=True)
            p.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    if args.command == "qualify":
        from waypoint.evidence.qualification import qualify

        cap = qualify(
            load_capability(args.artifact),
            [Path(p) for p in args.runs],
        )
        with Path(args.out).open("x") as f:
            f.write(cap.model_dump_json(indent=2) + "\n")
        print(f"Validation annotations saved to {args.out}")
        return
    if args.command == "inspect":
        from waypoint.inspector.render import render_inspector

        cap = load_capability(args.artifact)
        render_inspector(cap, [Path(p) for p in args.runs], Path(args.out))
        print(Path(args.out).resolve())
        return
    if args.command == "fixture":
        from waypoint.demo.member_console import FixtureServer

        with FixtureServer(args.port) as server:
            print(f"Synthetic fixture: {server.url}", flush=True)
            try:
                import threading

                threading.Event().wait()
            except KeyboardInterrupt:
                return
    else:
        from waypoint.app.workflow import execute

        raise SystemExit(asyncio.run(execute(args)))


def load_capability(path):
    data = json.loads(Path(path).read_text())
    if data.get("schema_version") != "2.0":
        raise ValueError("Only schema 2.0 is supported; rediscover legacy workflows")
    from waypoint.domain.artifact import Capability

    return Capability.model_validate(data)


if __name__ == "__main__":
    main()
