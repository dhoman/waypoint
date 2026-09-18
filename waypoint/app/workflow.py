"""URL + goal + named inputs; there is no application profile registry."""

import asyncio
import json
from pathlib import Path

from waypoint.app.handoff import interact
from waypoint.domain.artifact import Capability
from waypoint.evidence.trace import Trace
from waypoint.runtime.replay import Replay
from waypoint.surfaces.browser.policy import Policy
from waypoint.surfaces.browser.session import Browser


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
        from waypoint.discovery.loop import discover
        from waypoint.discovery.models import Decision
        from waypoint.discovery.prompt import PROMPT
        from waypoint.providers.openai import OpenAIProvider

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
