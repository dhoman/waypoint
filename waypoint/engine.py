"""Strict replay: artifact + runtime surface + inputs. No provider dependency."""

from collections import Counter
from decimal import Decimal, InvalidOperation
from time import monotonic

from waypoint.evidence import Trace, sanitized
from waypoint.recognition import holds, recognize
from waypoint.schema import Capability, Inputs, Invoice, Result, Summary
from waypoint.surface import Surface


def extract_summary(obs, inputs):
    if obs.fields.get("Member ID") != inputs.memberId:
        raise ValueError("identity: output entity differs")
    tables = [t for t in obs.tables if t["caption"] == "Invoice ledger"]
    if len(tables) != 1 or tables[0]["headers"] != ["Invoice", "Amount USD", "Status"]:
        raise ValueError("output: unsupported invoice table")
    invoices, amounts = [], []
    for row in tables[0]["rows"]:
        if len(row) != 3:
            raise ValueError("output: malformed invoice row")
        try:
            amount = Decimal(row[1])
        except InvalidOperation as exc:
            raise ValueError("output: invalid amount") from exc
        invoices.append(Invoice(invoice_id=row[0], amount=float(amount), status=row[2]))
        amounts.append(amount)
    if len({i.invoice_id for i in invoices}) != len(invoices):
        raise ValueError("output: duplicate invoice IDs")
    return Summary(
        memberId=inputs.memberId,
        invoices=invoices,
        total=float(sum(amounts, Decimal(0))),
    )


def choose_transition(cap, state, obs, inputs):
    matches = [
        t
        for t in cap.transitions
        if t.source == state and all(holds(p, obs, inputs) for p in t.guards)
    ]
    if len(matches) != 1:
        raise ValueError(
            "ambiguous transitions" if matches else "no valid transition guard"
        )
    return matches[0]


class Replay:
    def __init__(
        self, capability: Capability, surface: Surface, inputs: Inputs, trace: Trace
    ):
        self.cap = Capability.model_validate(capability.model_dump())
        self.surface, self.inputs, self.trace = surface, inputs, trace
        self.state = self.cap.entry
        self.transition = None
        self.outputs = None
        self.visits = Counter()
        self.steps = 0
        self.last_obs = None
        self.expected = []

    async def _observe(self, timeout_s=5):
        started = monotonic()
        obs = await self.surface.observe()
        self.last_obs = obs
        recognition = recognize(self.cap.screens, obs, self.inputs)
        self.trace.emit(
            "recognition",
            state=self.state,
            transition=self.transition,
            kind=recognition.kind,
            screen=recognition.screen,
            checks=recognition.checks,
            observation=sanitized(obs),
            duration_s=monotonic() - started,
            timing="observation_recognition",
        )
        if recognition.kind == "transient":
            started = monotonic()
            await self.surface.wait_ready(timeout_s)
            self.trace.emit(
                "wait",
                state=self.state,
                transition=self.transition,
                timing="application_wait",
                duration_s=monotonic() - started,
            )
            obs = await self.surface.observe()
            self.last_obs = obs
            recognition = recognize(self.cap.screens, obs, self.inputs)
        return obs, recognition

    async def run(self):
        try:
            while self.steps < self.cap.max_steps:
                state = self.cap.states[self.state]
                if state.outcome:
                    return self._result(
                        "succeeded"
                        if state.outcome == "succeeded"
                        else "business_outcome",
                        business_code=None
                        if state.outcome == "succeeded"
                        else state.outcome,
                    )
                obs, recognition = await self._observe()
                if recognition.kind == "unknown":
                    return await self._stop(
                        "awaiting_intervention",
                        "unknown",
                        "Unknown or blocking observation",
                    )
                if recognition.kind != "recognized":
                    raise ValueError("ambiguous or unsupported recognition")
                if recognition.screen != state.screen:
                    raise ValueError("unexpected recognized destination")
                transition = choose_transition(self.cap, self.state, obs, self.inputs)
                self.transition = transition.id
                self.expected = [
                    self.cap.states[transition.destination].screen
                    or transition.destination
                ]
                self.visits[self.state] += 1
                if self.visits[self.state] > self.cap.max_visits:
                    raise ValueError("bounded cycle exhausted")
                self.trace.emit(
                    "transition_started",
                    state=self.state,
                    transition=transition.id,
                    destination=transition.destination,
                    action=transition.action.model_dump(),
                    guards=[
                        {
                            "predicate": p.model_dump(),
                            "passed": holds(p, obs, self.inputs),
                        }
                        for p in transition.guards
                    ],
                )
                if transition.risk == "write":
                    raise ValueError("policy: writes are disabled")
                if transition.action.kind == "extract":
                    self.outputs = extract_summary(obs, self.inputs)
                elif transition.action.kind != "outcome":
                    await self.surface.act(transition.action, self.inputs)
                self.steps += 1
                destination = transition.destination
                if not self.cap.states[transition.destination].outcome:
                    post, recognized = await self._observe(transition.timeout_s)
                    if recognized.kind == "unknown":
                        return await self._stop(
                            "awaiting_intervention",
                            "unknown",
                            "Unexpected blocking observation after action",
                        )
                    candidates = [
                        dest
                        for dest in [transition.destination, *transition.alternatives]
                        if self.cap.states[dest].screen == recognized.screen
                        and all(
                            holds(p, post, self.inputs)
                            for p in transition.alternatives.get(
                                dest, transition.postconditions
                            )
                        )
                    ]
                    if recognized.kind != "recognized" or len(candidates) != 1:
                        raise ValueError("unexpected or ambiguous destination")
                    destination = candidates[0]
                self.state = destination
                self.trace.emit(
                    "transition_completed", state=self.state, transition=transition.id
                )
            raise ValueError("maximum steps exhausted")
        except Exception as exc:
            category = (
                "identity"
                if "identity" in str(exc)
                else "policy"
                if "policy" in str(exc)
                else "ambiguity"
                if "ambiguous" in str(exc)
                else "execution"
            )
            return await self._stop("failed", category, str(exc))

    def _result(self, status, **kwargs):
        result = Result(
            run_id=self.trace.run_id,
            capability_id=self.cap.capability_id,
            revision=self.cap.revision,
            status=status,
            outputs=self.outputs if status == "succeeded" else None,
            state=self.state,
            transition=self.transition,
            expected=self.expected,
            observed=sanitized(self.last_obs) if self.last_obs else {},
            **kwargs,
        )
        self.trace.save("result.json", result.model_dump())
        self.trace.emit(
            "result",
            **result.model_dump(exclude={"run_id", "capability_id", "revision"}),
        )
        return result

    async def _stop(self, status, category, reason):
        evidence = await self.surface.capture(
            self.trace.directory, f"failure-{self.trace.sequence}"
        )
        return self._result(
            status, failure_category=category, reason=reason, evidence=evidence
        )
