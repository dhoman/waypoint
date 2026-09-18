import argparse
import asyncio
import os
from pathlib import Path

from waypoint.browser import BrowserSurface
from waypoint.engine import Replay
from waypoint.evidence import Trace
from waypoint.schema import Capability, Inputs


async def execute(args):
    inputs = Inputs(memberId=args.member)
    if args.command == "discover":
        # Provider dependencies are only loaded on this branch.
        from waypoint.discovery import discover
        from waypoint.provider import OpenAIProvider

        provider = OpenAIProvider(args.model)
        trace = Trace(args.out, kind="discovery")
        async with BrowserSurface(args.url, headed=args.headed) as surface:
            cap = await discover(args.goal, surface, inputs, provider, trace)
        print(
            f"{'Discovery complete' if cap else 'Discovery failed'}: {args.out}/result.json"
        )
        return 0 if cap else 1
    cap = Capability.model_validate_json(Path(args.artifact).read_text())
    trace = Trace(args.out, cap)
    async with BrowserSurface(args.url, headed=args.headed) as surface:
        result = await Replay(cap, surface, inputs, trace).run()
    print(result.model_dump_json(indent=2))
    return 0 if result.status in {"succeeded", "business_outcome"} else 2


def main():
    parser = argparse.ArgumentParser(
        description="Discover once; replay without a model"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixture")
    fixture.add_argument("--port", type=int, default=8765)
    amend = commands.add_parser("amend")
    amend.add_argument("--artifact", required=True)
    amend.add_argument("--out", required=True)
    for command in ("discover", "replay"):
        p = commands.add_parser(command)
        p.add_argument("--url", default="http://127.0.0.1:8765/")
        p.add_argument("--member", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--headed", action="store_true")
        if command == "discover":
            p.add_argument(
                "--goal",
                default="Find the requested member and return their invoice summary.",
            )
            p.add_argument("--model", default=os.environ.get("WAYPOINT_MODEL"))
        else:
            p.add_argument("--artifact", required=True)
    args = parser.parse_args()
    if args.command == "amend":
        from waypoint.compiler import amend_missing_member

        cap = amend_missing_member(
            Capability.model_validate_json(Path(args.artifact).read_text())
        )
        with Path(args.out).open("x") as f:
            f.write(cap.model_dump_json(indent=2) + "\n")
        print(f"Authored revision {cap.revision}: {args.out}")
        return
    if args.command == "fixture":
        from waypoint.fixture import FixtureServer

        with FixtureServer(args.port) as server:
            print(f"Synthetic fixture: {server.url}", flush=True)
            try:
                import threading

                threading.Event().wait()
            except KeyboardInterrupt:
                return
    else:
        raise SystemExit(asyncio.run(execute(args)))


if __name__ == "__main__":
    main()
