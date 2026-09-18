import argparse
import asyncio
import json
import os
from pathlib import Path

from waypoint.browser import BrowserSurface
from waypoint.engine import Replay
from waypoint.evidence import Trace
from waypoint.schema import Capability, Inputs


async def execute(args):
    is_v2 = (
        args.command == "replay"
        and json.loads(Path(args.artifact).read_text()).get("schema_version") == "2.0"
    )
    if is_v2 or (args.command == "discover" and args.member is None):
        from waypoint.web.cli import execute as execute_web

        return await execute_web(args)
    args.url = args.url or "http://127.0.0.1:8765/"
    inputs = Inputs(memberId=args.member)
    if args.command == "discover":
        # Provider dependencies are only loaded on this branch.
        from waypoint.discovery import discover
        from waypoint.provider import OpenAIProvider

        provider = OpenAIProvider(args.model)
        trace = Trace(args.out, kind="discovery")
        async with BrowserSurface(args.url, headed=args.headed) as surface:
            cap = await discover(
                args.goal
                or "Find the requested member and return their invoice summary.",
                surface,
                inputs,
                provider,
                trace,
            )
        print(
            f"{'Discovery complete' if cap else 'Discovery failed'}: {args.out}/result.json"
        )
        return 0 if cap else 1
    cap = Capability.model_validate_json(Path(args.artifact).read_text())
    trace = Trace(args.out, cap)
    if args.interactive and not args.headed:
        raise ValueError("Interactive handoff requires --headed")
    async with BrowserSurface(args.url, headed=args.headed) as surface:
        runner = Replay(cap, surface, inputs, trace)
        result = await runner.run()
        while result.status == "awaiting_intervention" and args.interactive:
            token = surface.ownership.token
            print(
                f"PAUSED {trace.run_id} at {runner.transition}: {result.reason}",
                flush=True,
            )
            print(
                f"Same browser remains live. Commands: take {token} | resume {token} | cancel",
                flush=True,
            )
            while surface.ownership.state != "automation":
                try:
                    command = await asyncio.to_thread(input, "control> ")
                    parts = command.strip().split()
                    if parts == ["cancel"]:
                        result = runner.cancel()
                        break
                    if parts == ["take", token]:
                        runner.take_control(token)
                        print(
                            "Human owns the browser. Dismiss the notice or navigate to an allowed checkpoint, then resume.",
                            flush=True,
                        )
                    elif parts == ["resume", token]:
                        if not await runner.resume(token):
                            print(
                                "Resume rejected; human retains control. Restore a matching identity/checkpoint.",
                                flush=True,
                            )
                    else:
                        print("Invalid or stale command.", flush=True)
                except EOFError:
                    result = runner.cancel()
                    break
                except ValueError as exc:
                    print(str(exc), flush=True)
            if result.status == "cancelled":
                break
            result = await runner.run()
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
        p.add_argument("--member", help="Version 1 member-console compatibility mode")
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
        from waypoint.qualification import qualify

        cap = qualify(
            load_capability(args.artifact),
            [Path(p) for p in args.runs],
        )
        with Path(args.out).open("x") as f:
            f.write(cap.model_dump_json(indent=2) + "\n")
        print(f"Validation annotations saved to {args.out}")
        return
    if args.command == "inspect":
        from waypoint.inspector import render_inspector

        cap = load_capability(args.artifact)
        render_inspector(cap, [Path(p) for p in args.runs], Path(args.out))
        print(Path(args.out).resolve())
        return
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


def load_capability(path):
    data = json.loads(Path(path).read_text())
    if data.get("schema_version") == "2.0":
        from waypoint.web.schema import Capability as WebCapability

        return WebCapability.model_validate(data)
    return Capability.model_validate(data)


if __name__ == "__main__":
    main()
