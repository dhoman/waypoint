"""URL + goal + named inputs; there is no application profile registry."""

import asyncio
import json
from pathlib import Path

from waypoint.evidence import Trace
from waypoint.web.browser import Browser
from waypoint.web.policy import Policy
from waypoint.web.runtime import Replay
from waypoint.web.schema import Capability


def parse_inputs(bindings):
    inputs = {}
    for binding in bindings:
        if "=" not in binding:
            raise ValueError("--input must be NAME=VALUE")
        key, value = binding.split("=", 1)
        if not key or key in inputs:
            raise ValueError("empty or duplicate input name")
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        if value is None or isinstance(value, (dict, list)):
            raise ValueError("inputs must be scalar strings, numbers or booleans")
        inputs[key] = value
    return inputs


async def interact(runner, browser, result):
    while result.status == "awaiting_intervention":
        token = browser.ownership.token
        print(
            f"PAUSED {runner.trace.run_id} at {runner.transition}: {result.reason}",
            flush=True,
        )
        print(f"Commands: take {token} | resume {token} | cancel", flush=True)
        while browser.ownership.state != "automation":
            try:
                parts = (await asyncio.to_thread(input, "control> ")).strip().split()
                if parts == ["cancel"]:
                    return runner.cancel()
                if parts == ["take", token]:
                    runner.take_control(token)
                    print("Human owns this browser.", flush=True)
                elif parts == ["resume", token]:
                    if not await runner.resume(token):
                        print(
                            "Resume rejected; restore an allowed checkpoint and identity.",
                            flush=True,
                        )
                else:
                    print("Invalid or stale command.", flush=True)
            except EOFError:
                return runner.cancel()
            except ValueError as exc:
                print(str(exc), flush=True)
        result = await runner.run()
    return result


async def execute(args):
    inputs = parse_inputs(args.input)
    cap = (
        Capability.model_validate_json(Path(args.artifact).read_text())
        if args.command == "replay"
        else None
    )
    url = args.url or (cap.origin + cap.entry_path if cap else None)
    if not url:
        raise ValueError("Generic discovery requires --url")
    if args.command == "discover" and not args.goal:
        raise ValueError("Generic discovery requires --goal")
    if (getattr(args, "interactive", False) or args.prepare) and not args.headed:
        raise ValueError("Manual control requires --headed")
    if cap:
        cap.validate_inputs(inputs)
    policy = Policy.for_url(
        url,
        allowed_origins=args.allow_origin,
        allowed_controls=args.allow_control,
        allowed_methods=args.allow_method,
    )
    trace = Trace(args.out, cap, kind="replay" if cap else "discovery")
    trace.emit(
        "runtime_policy",
        origins=sorted(policy.origins),
        allowed_controls=sorted(policy.allowed_controls),
        allowed_methods=sorted(policy.allowed_methods),
    )
    async with Browser(url, headed=args.headed, policy=policy) as browser:
        browser.event_sink = trace.emit
        if args.prepare:
            token = browser.ownership.request()
            browser.ownership.take(token)
            print(
                "Prepare this browser manually (for example, sign in), then press Enter here.",
                flush=True,
            )
            await asyncio.to_thread(input)
            browser.ownership.begin_resume(token)
            await browser.observe()
            browser.ownership.finish_resume(valid=True)
        if cap:
            runner = Replay(cap, browser, inputs, trace)
            result = await runner.run()
            if args.interactive:
                result = await interact(runner, browser, result)
            print(result.model_dump_json(indent=2, exclude={"observed"}))
            return 0 if result.status in {"succeeded", "business_outcome"} else 2
        from waypoint.provider import OpenAIProvider
        from waypoint.web.discovery import PROMPT, Decision, discover

        provider = OpenAIProvider(
            args.model, decision_type=Decision, instructions=PROMPT
        )
        artifact = await discover(
            args.goal,
            browser,
            inputs,
            provider,
            trace,
            max_steps=args.max_steps,
            timeout_s=args.timeout,
        )
        print(
            f"{'Discovery complete' if artifact else 'Discovery failed'}: {args.out}/result.json"
        )
        return 0 if artifact else 1
