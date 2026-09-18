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
            p.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    if args.command == "qualify":
        from waypoint.qualification import qualify

        cap = qualify(
            Capability.model_validate_json(Path(args.artifact).read_text()),
            [Path(p) for p in args.runs],
        )
        with Path(args.out).open("x") as f:
            f.write(cap.model_dump_json(indent=2) + "\n")
        print(f"Validation annotations saved to {args.out}")
        return
    if args.command == "inspect":
        from waypoint.inspector import render_inspector

        cap = Capability.model_validate_json(Path(args.artifact).read_text())
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


if __name__ == "__main__":
    main()
