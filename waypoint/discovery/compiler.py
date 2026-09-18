import hashlib
import json
from collections import Counter

from waypoint.domain.artifact import Action, Capability, State, Transition
from waypoint.surfaces.protocol import SurfaceBinding


def compile_route(
    observations,
    actions,
    proposals,
    output,
    *,
    inputs,
    goal,
    binding: SurfaceBinding,
    run_id,
    provider,
    model,
):
    if len(observations) != len(actions) + 1 or len(proposals) != len(observations):
        raise ValueError("incomplete observed route")
    screens, states, transitions = {}, {}, []
    signatures = {}
    for i, screen in enumerate(proposals):
        signature = json.dumps(
            [p.model_dump() for p in screen.recognition], sort_keys=True
        )
        if signature in signatures:
            sid = signatures[signature]
            if screens[sid].identity != screen.identity:
                raise ValueError(
                    "screen equivalence has inconsistent identity bindings"
                )
        else:
            sid = screen.id
            if sid in screens:
                sid += "_" + hashlib.sha256(signature.encode()).hexdigest()[:6]
            screen = screen.model_copy(deep=True, update={"id": sid})
            screen.provenance.evidence = [f"{run_id}/events.jsonl"]
            screens[sid] = screen
            signatures[signature] = sid
        states[f"s{i}"] = State(id=f"s{i}", screen=sid, progress=f"before_action_{i}")
    counts = Counter(state.screen for state in states.values())
    for state in states.values():
        state.checkpoint = counts[state.screen] == 1
    states["done"] = State(id="done", progress="terminal", outcome="succeeded")
    for i, action in enumerate([*actions, Action(kind="extract")]):
        dest = f"s{i + 1}" if i < len(actions) else "done"
        transitions.append(
            Transition(
                id=f"t{i}",
                source=f"s{i}",
                destination=dest,
                action=action,
                guards=screens[states[f"s{i}"].screen].identity,
                risk="navigation" if action.kind == "click" else "read",
            )
        )
    cap = Capability(
        capability_id="web-" + hashlib.sha256(goal.encode()).hexdigest()[:10],
        description=goal,
        app=observations[0].title or binding.origin,
        surface=binding.surface,
        origin=binding.origin,
        entry_path=binding.entry_path,
        required_inputs={
            k: "boolean"
            if isinstance(v, bool)
            else "number"
            if isinstance(v, (int, float))
            else "string"
            for k, v in inputs.items()
        },
        output=output,
        entry="s0",
        screens=screens,
        states=states,
        transitions=transitions,
        terminals=["done"],
        discovery_run=run_id,
        provider=provider,
        model=model,
    )
    cap.validate_inputs(inputs)
    return cap
