"""Compile observed actions, preserving route order and explicit input bindings."""

from waypoint.recognition import holds
from waypoint.schema import (
    Action,
    Capability,
    Inputs,
    Predicate,
    Provenance,
    Screen,
    State,
    Transition,
    screen_id,
)


def amend_missing_member(cap: Capability) -> Capability:
    """Explicit authored revision; never implies discovery of the unseen branch."""
    cap = cap.model_copy(deep=True)
    if "missing" in cap.states:
        raise ValueError("missing-member amendment already applied")
    identity = Predicate(op="field_equals_input", field="Search ID", input="memberId")
    cap.screens["no_members"] = Screen(
        id="no_members",
        recognition=[
            Predicate(op="heading", value="No members found"),
            Predicate(op="no_dialog"),
        ],
        identity=identity,
        fields=["Search ID"],
        provenance=Provenance(
            origin="authored",
            note="Developer-authored missing-member branch; not observed in happy-path discovery.",
        ),
    )
    cap.states["missing"] = State(
        id="missing",
        screen="no_members",
        progress="terminal",
        outcome="member_not_found",
    )
    searches = [
        t
        for t in cap.transitions
        if t.action.target
        and t.action.target.name == "Search"
        and t.action.kind == "click"
    ]
    if len(searches) != 1:
        raise ValueError("amendment requires one observed search")
    searches[0].alternatives["missing"] = [
        Predicate(op="heading", value="No members found"),
        identity,
    ]
    cap.terminals.append("missing")
    cap.revision += 1
    cap.status = "draft"
    cap.amendments.append(
        "Revision adds an authored missing-member outcome after Search; requires separate validation."
    )
    return Capability.model_validate(cap.model_dump())


def compile_route(steps, *, run_id, provider, model, goal):
    if not steps:
        raise ValueError("empty route")
    screens, states, transitions = {}, {}, []
    observations = [s[0] for s in steps] + [steps[-1][2]]
    for i, obs in enumerate(observations):
        if len(obs.headings) != 1 or obs.dialog or obs.loading:
            raise ValueError("only stable unblocked observations can be compiled")
        sid = screen_id(obs.headings[0])
        identity_field = next(
            (k for k in ("Member ID", "Search ID") if k in obs.fields), None
        )
        identity = (
            Predicate(op="field_equals_input", field=identity_field, input="memberId")
            if identity_field
            else None
        )
        predicates = [
            Predicate(op="heading", value=obs.headings[0]),
            Predicate(op="no_dialog"),
        ]
        if obs.tables:
            predicates.append(
                Predicate(op="table_present", value=obs.tables[0]["caption"])
            )
        provenance = Provenance(
            origin="discovered" if provider != "test" else "authored",
            note="Observed UI landmarks; same-heading equivalence checked against every captured observation, cross-input validation still required.",
            evidence=[f"{run_id}/events.jsonl"],
            validated=False,
        )
        candidate = Screen(
            id=sid,
            recognition=predicates,
            identity=identity,
            fields=list(obs.fields),
            provenance=provenance,
        )
        if sid in screens:
            existing = screens[sid]
            demo_input = Inputs(
                memberId=obs.fields.get(
                    "Member ID", obs.fields.get("Search ID", "M-101")
                )
            )
            if existing.identity != candidate.identity or not all(
                holds(p, obs, demo_input) for p in existing.recognition
            ):
                raise ValueError(
                    "candidate screen equivalence failed deterministic validation"
                )
        else:
            screens[sid] = candidate
        progress = (
            "invoices"
            if obs.tables and obs.tables[0]["caption"] == "Invoice ledger"
            else "identity_verified"
            if identity_field == "Member ID"
            else "results"
            if identity_field
            else "query_bound"
            if i and steps[i - 1][1].kind == "fill"
            else "search"
        )
        states[f"s{i}"] = State(
            id=f"s{i}",
            screen=sid,
            progress=progress,
            checkpoint=progress in {"identity_verified", "invoices"},
        )
    for i, (_, action, _) in enumerate(steps):
        source, dest = states[f"s{i}"], states[f"s{i + 1}"]
        guards = [Predicate(op="no_dialog")]
        if source.progress == "query_bound":
            guards.append(
                Predicate(op="input_value", field="Member ID", input="memberId")
            )
        if screens[source.screen].identity:
            guards.append(screens[source.screen].identity)
        if action.target:
            screens[source.screen].controls[f"action_{i}"] = action.target
        transitions.append(
            Transition(
                id=f"t{i}",
                source=source.id,
                destination=dest.id,
                action=action,
                guards=guards,
                postconditions=[screens[dest.screen].identity]
                if screens[dest.screen].identity
                else [],
                risk="navigation" if action.kind == "click" else "read",
                provenance=Provenance(
                    origin="discovered" if provider != "test" else "authored",
                    note="Exact observed action; no detours removed.",
                    evidence=[f"{run_id}/events.jsonl"],
                    validated=False,
                ),
            )
        )
    final = states[f"s{len(steps)}"]
    if final.progress != "invoices":
        raise ValueError("route did not reach the supported invoice output contract")
    states["done"] = State(id="done", progress="terminal", outcome="succeeded")
    transitions.append(
        Transition(
            id="extract",
            source=final.id,
            destination="done",
            action=Action(kind="extract"),
            guards=[
                screens[final.screen].identity,
                Predicate(op="table_present", value="Invoice ledger"),
            ],
            provenance=Provenance(
                origin="authored",
                note="Typed output contract: Invoice ledger columns Invoice / Amount USD / Status; independently read from final UI.",
            ),
        )
    )
    return Capability(
        description=goal,
        entry="s0",
        screens=screens,
        states=states,
        transitions=transitions,
        terminals=["done"],
        discovery_run=run_id,
        provider=provider,
        model=model,
        amendments=[
            "Typed invoice extraction and screen identity rules are developer-authored contracts, not inferred application completeness."
        ],
    )
