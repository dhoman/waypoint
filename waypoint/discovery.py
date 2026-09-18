"""LLM chooses each action from fresh UI observations. Replay never imports this."""

import asyncio
from time import monotonic
from typing import Literal, Protocol

from pydantic import Field

from waypoint.compiler import compile_route
from waypoint.engine import extract_summary
from waypoint.evidence import sanitized
from waypoint.schema import Action, Model, Target


class Decision(Model):
    operation: Literal["fill", "click", "wait", "finish"]
    target: Target | None
    input: Literal["memberId"] | None
    rationale: str = Field(max_length=240)


class Provider(Protocol):
    name: str
    model: str

    async def decide(self, goal, inputs, observation, history) -> Decision: ...


async def discover(
    goal, surface, inputs, provider: Provider, trace, *, max_steps=16, timeout_s=120
):
    steps, history = [], []
    previous, repeats = None, 0
    try:
        async with asyncio.timeout(timeout_s):
            for _ in range(max_steps):
                started = monotonic()
                before = await surface.observe()
                trace.emit(
                    "observation",
                    observation=sanitized(before),
                    timing="observation_recognition",
                    duration_s=monotonic() - started,
                )
                for key in ("Member ID", "Search ID"):
                    if key in before.fields and before.fields[key] != inputs.memberId:
                        raise ValueError("identity mismatch")
                if before.dialog or before.readonly:
                    raise ValueError("unknown blocking observation")
                signature = before.model_dump_json()
                repeats = repeats + 1 if signature == previous else 0
                previous = signature
                if repeats >= 2:
                    raise ValueError("no_progress")
                started = monotonic()
                decision = await provider.decide(goal, inputs, before, history)
                trace.emit(
                    "model_decision",
                    operation=decision.operation,
                    target=decision.target.model_dump() if decision.target else None,
                    input=decision.input,
                    rationale=decision.rationale,
                    provider=provider.name,
                    model=provider.model,
                    timing="model_inference",
                    duration_s=monotonic() - started,
                )
                if decision.operation == "finish":
                    outputs = extract_summary(before, inputs)
                    cap = compile_route(
                        steps,
                        run_id=trace.run_id,
                        provider=provider.name,
                        model=provider.model,
                        goal=goal,
                    )
                    trace.save("capability.json", cap.model_dump())
                    trace.save(
                        "result.json",
                        {
                            "status": "succeeded",
                            "run_id": trace.run_id,
                            "outputs": outputs.model_dump(),
                            "kind": "genuine_discovery"
                            if provider.name == "openai"
                            else "test_only",
                        },
                    )
                    trace.emit(
                        "discovery_completed",
                        outputs=outputs.model_dump(),
                        actions=len(steps),
                    )
                    await surface.capture(trace.directory, "completed")
                    return cap
                if decision.operation == "wait":
                    await surface.wait_ready(5)
                    history.append({"operation": "wait"})
                    continue
                action = Action(
                    kind=decision.operation,
                    target=decision.target,
                    input=decision.input,
                )
                await surface.act(action, inputs)
                after = await surface.observe()
                if after.loading:
                    await surface.wait_ready(5)
                    after = await surface.observe()
                steps.append((before, action, after))
                history.append(action.model_dump())
                trace.emit(
                    "action_completed",
                    action=action.model_dump(),
                    before=sanitized(before),
                    after=sanitized(after),
                )
            raise ValueError("step_limit")
    except Exception as exc:
        # Do not persist provider exception bodies: they may contain submitted UI
        # content. Failure category plus exception class is sufficient here.
        category = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        evidence = await surface.capture(trace.directory, "failure")
        trace.save(
            "result.json",
            {"status": "failed", "failure_category": category, "evidence": evidence},
        )
        trace.emit("discovery_failed", category=category)
        return None
