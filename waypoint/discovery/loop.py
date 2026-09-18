"""Generic observe/decide/act discovery. Application rules are model proposals."""

import asyncio
import re
from time import monotonic

from waypoint.discovery.compiler import compile_route
from waypoint.discovery.models import Provider
from waypoint.domain.artifact import Action, Predicate, Screen
from waypoint.evidence.trace import sanitized
from waypoint.runtime.interpret import check, extract
from waypoint.surfaces.protocol import Surface


def parameterize(decision, observation, inputs):
    """Conservative exact-value bindings, checked on this observation before use."""
    screen = Screen(**decision.screen.model_dump())
    for predicate in list(screen.recognition):
        if predicate.op in {"field_equals_input", "target_text_input"}:
            screen.recognition.remove(predicate)
            if predicate not in screen.identity:
                screen.identity.append(predicate)
    if not screen.recognition:
        raise ValueError(
            "screen requires stable landmarks separate from entity bindings"
        )
    if any(
        p.op == "text_present" and re.search(r"\d", p.value) for p in screen.recognition
    ):
        raise ValueError(
            "screen type cannot depend on numeric text such as result counts; use a stable heading or target"
        )
    for key, value in inputs.items():
        matches = [name for name, v in inputs.items() if v == value]
        if len(matches) != 1:
            continue
        for p in screen.recognition:
            if p.op == "heading" and p.value == str(value):
                p.op = "heading_input"
                p.input = key
                p.value = ""
        for field, observed in observation.fields.items():
            if not field.startswith("input:") and observed == str(value):
                binding = Predicate(op="field_equals_input", field=field, input=key)
                if binding not in screen.identity:
                    screen.identity.append(binding)
    screen.identity.sort(key=lambda p: p.model_dump_json())
    screen.recognition.sort(key=lambda p: p.model_dump_json())
    return screen


async def discover(
    goal,
    surface: Surface,
    inputs,
    provider: Provider,
    trace,
    *,
    max_steps=30,
    timeout_s=240,
):
    surface.event_sink = trace.emit
    observations, actions, screens, history = [], [], [], []
    last_signature = None
    repeats = 0
    try:
        async with asyncio.timeout(timeout_s):
            for _ in range(max_steps):
                started = monotonic()
                obs = await surface.observe()
                trace.emit(
                    "observation",
                    observation=sanitized(obs),
                    timing="observation_recognition",
                    duration_s=monotonic() - started,
                )
                if obs.dialog:
                    raise ValueError("blocking dialog requires manual intervention")
                signature = obs.model_dump_json()
                repeats = repeats + 1 if signature == last_signature else 0
                last_signature = signature
                if repeats >= 3:
                    raise ValueError("no_progress")
                started = monotonic()
                decision = await provider.decide(goal, inputs, obs, history)
                trace.emit(
                    "model_decision",
                    operation=decision.operation,
                    target=decision.target.model_dump() if decision.target else None,
                    input=decision.input,
                    screen=decision.screen.model_dump(),
                    outputs=[o.model_dump() for o in decision.outputs],
                    provider=provider.name,
                    model=provider.model,
                    rationale=decision.rationale,
                    timing="model_inference",
                    duration_s=monotonic() - started,
                )
                try:
                    screen = parameterize(decision, obs, inputs)
                    if not all(await check(screen.recognition, obs, inputs, surface)):
                        raise ValueError(
                            "model screen proposal does not recognize current UI"
                        )
                    if not all(await check(screen.identity, obs, inputs, surface)):
                        raise ValueError(
                            "identity binding rejected before action: field_equals_input requires an observed field equal to the input; target_text_input compares the target's OWN text, not its containing row. Correct the proposed predicate, never the requested identity."
                        )
                    if decision.operation not in {"finish", "wait"}:
                        action = Action(
                            kind=decision.operation,
                            target=decision.target,
                            input=decision.input,
                            value=decision.value,
                        )
                        refs = [
                            action.input,
                            action.target.name_input,
                            action.target.row_input,
                        ]
                        if any(ref and ref not in inputs for ref in refs):
                            raise ValueError(
                                "unknown action or locator input; references must be parameter keys"
                            )
                        if (
                            action.target.name_input
                            and action.target.name
                            and action.target.name
                            != str(inputs[action.target.name_input])
                        ):
                            raise ValueError(
                                "name_input replaces the target label, not its typed value. This label is constant: set target.name_input=null and keep action.input for the value to type."
                            )
                        await surface.resolve(action.target, inputs)
                    if decision.operation == "finish":
                        if not decision.outputs:
                            raise ValueError("finish requires typed extraction rules")
                        outputs = await extract(decision.outputs, obs, inputs, surface)
                except ValueError as exc:
                    # Discovery may revise a rejected proposal; no action was delivered.
                    # Replay has no equivalent model fallback or artifact mutation.
                    trace.emit("proposal_rejected", reason=str(exc))
                    history.append(
                        {
                            "operation": "proposal_rejected",
                            "reason": str(exc),
                            "proposal": decision.model_dump(),
                        }
                    )
                    continue
                if decision.operation == "wait":
                    await surface.settle(10)
                    history.append({"operation": "wait"})
                    continue
                observations.append(obs)
                screens.append(screen)
                if decision.operation == "finish":
                    cap = compile_route(
                        observations,
                        actions,
                        screens,
                        decision.outputs,
                        inputs=inputs,
                        goal=goal,
                        binding=surface.binding,
                        run_id=trace.run_id,
                        provider=provider.name,
                        model=provider.model,
                    )
                    trace.capability = cap
                    trace.save("capability.json", cap.model_dump())
                    trace.save(
                        "result.json",
                        {
                            "status": "succeeded",
                            "run_id": trace.run_id,
                            "capability_id": cap.capability_id,
                            "revision": 1,
                            "outputs": outputs,
                            "kind": "genuine_discovery"
                            if provider.name == "openai"
                            else "test_only",
                        },
                    )
                    trace.emit(
                        "discovery_completed", outputs=outputs, actions=len(actions)
                    )
                    await surface.capture(trace.directory, "completed")
                    return cap
                action = Action(
                    kind=decision.operation,
                    target=decision.target,
                    input=decision.input,
                    value=decision.value,
                )
                if action.input and action.input not in inputs:
                    raise ValueError("unknown action input")
                if action.target:
                    for ref in (action.target.name_input, action.target.row_input):
                        if ref and ref not in inputs:
                            raise ValueError("unknown locator input")
                await surface.act(action, inputs)
                after = await surface.observe()
                actions.append(action)
                history.append(
                    {
                        "operation": decision.operation,
                        "status": "completed",
                        "action": action.model_dump(),
                    }
                )
                trace.emit(
                    "action_completed",
                    action=action.model_dump(),
                    before=sanitized(obs),
                    after=sanitized(after),
                )
            raise ValueError("step_limit")
    except Exception as exc:
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        evidence = await surface.capture(trace.directory, "failure")
        trace.save(
            "result.json",
            {
                "status": "failed",
                "reason": reason,
                "failure_category": reason,
                "evidence": evidence,
            },
        )
        trace.emit("discovery_failed", reason=reason)
        return None
