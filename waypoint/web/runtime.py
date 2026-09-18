"""Generic artifact interpreter. No application names and no model imports."""

import asyncio
from time import monotonic

from waypoint.delivery import DeliveryLedger
from waypoint.evidence import sanitized
from waypoint.web.interpret import check, extract, recognize
from waypoint.web.policy import origin
from waypoint.web.schema import Capability, Result


class Replay:
    def __init__(self, capability, browser, inputs, trace):
        self.cap = Capability.model_validate(capability.model_dump())
        self.inputs = self.cap.validate_inputs(inputs)
        if origin(browser.url) != self.cap.origin:
            raise ValueError(
                "policy: artifact belongs to another origin; rediscover for this site"
            )
        self.browser, self.trace = browser, trace
        self.browser.event_sink = trace.emit
        self.state = self.cap.entry
        self.transition = None
        self.steps = 0
        self.obs = None
        self.outputs = None
        self.expected = []
        self.human_started = None
        self.delivery = DeliveryLedger()

    async def observe(self):
        start = monotonic()
        self.obs = await self.browser.observe()
        kind, screen, checks = await recognize(
            self.cap.screens, self.obs, self.inputs, self.browser
        )
        self.trace.emit(
            "recognition",
            state=self.state,
            transition=self.transition,
            kind=kind,
            screen=screen,
            checks=checks,
            observation=sanitized(self.obs),
            timing="observation_recognition",
            duration_s=monotonic() - start,
        )
        return kind, screen

    async def choose(self, state):
        matches = []
        for t in self.cap.transitions:
            if t.source == state and all(
                await check(t.guards, self.obs, self.inputs, self.browser)
            ):
                matches.append(t)
        if len(matches) != 1:
            raise ValueError(
                "ambiguous transitions" if matches else "no valid transition guards"
            )
        return matches[0]

    def result(self, status, **kwargs):
        if status != "awaiting_intervention":
            self.browser.ownership.terminate()
        result = Result(
            run_id=self.trace.run_id,
            capability_id=self.cap.capability_id,
            revision=self.cap.revision,
            status=status,
            state=self.state,
            transition=self.transition,
            outputs=self.outputs if status == "succeeded" else None,
            expected=self.expected,
            observed=sanitized(self.obs) if self.obs else {},
            **kwargs,
        )
        self.trace.save("result.json", result.model_dump())
        self.trace.emit(
            "result",
            **result.model_dump(exclude={"run_id", "capability_id", "revision"}),
        )
        return result

    async def stop(self, status, reason, category):
        evidence = await self.browser.capture(
            self.trace.directory, f"failure-{self.trace.sequence}"
        )
        if status == "awaiting_intervention":
            self.browser.ownership.request()
            self.human_started = monotonic()
            self.trace.emit(
                "intervention_requested",
                state=self.state,
                transition=self.transition,
                reason=reason,
                evidence=evidence,
                permitted_checkpoints=[
                    s.id for s in self.cap.states.values() if s.checkpoint
                ],
            )
        return self.result(
            status, reason=reason, failure_category=category, evidence=evidence
        )

    async def run(self):
        self.browser.ownership.require_automation()
        try:
            while self.steps < self.cap.max_steps:
                state = self.cap.states[self.state]
                if state.outcome:
                    return self.result(
                        "succeeded"
                        if state.outcome == "succeeded"
                        else "business_outcome",
                        business_code=None
                        if state.outcome == "succeeded"
                        else state.outcome,
                    )
                kind, screen = await self.observe()
                if kind in {"unknown", "transient"}:
                    return await self.stop(
                        "awaiting_intervention",
                        "Unrecognized or blocking observation",
                        kind,
                    )
                if kind != "recognized" or screen != state.screen:
                    raise ValueError("ambiguous or unexpected screen")
                t = await self.choose(self.state)
                self.transition = t.id
                self.expected = [
                    self.cap.states[d].screen or d
                    for d in [t.destination, *t.alternatives]
                ]
                self.trace.emit(
                    "transition_started",
                    state=self.state,
                    transition=t.id,
                    destination=t.destination,
                    action=t.action.model_dump(),
                )
                async with asyncio.timeout(t.timeout_s):
                    # Refresh the screen and identity immediately before delivery.
                    kind, screen = await self.observe()
                    if kind != "recognized" or screen != state.screen:
                        raise ValueError("precondition changed before action")
                    if t.action.kind == "extract":
                        self.outputs = await extract(
                            self.cap.output, self.obs, self.inputs, self.browser
                        )
                    elif t.action.kind != "outcome":
                        await self.delivery.attempt(
                            t.id, lambda: self.browser.act(t.action, self.inputs)
                        )
                    dest = t.destination
                    if not self.cap.states[dest].outcome:
                        kind, screen = await self.observe()
                        if kind in {"unknown", "transient"}:
                            return await self.stop(
                                "awaiting_intervention",
                                "Unexpected observation after action",
                                kind,
                            )
                        candidates = []
                        for d in [t.destination, *t.alternatives]:
                            if self.cap.states[d].screen == screen and all(
                                await check(
                                    t.alternatives.get(d, t.postconditions),
                                    self.obs,
                                    self.inputs,
                                    self.browser,
                                )
                            ):
                                candidates.append(d)
                        if kind != "recognized" or len(candidates) != 1:
                            raise ValueError("ambiguous or unexpected destination")
                        dest = candidates[0]
                self.state = dest
                self.steps += 1
                if self.delivery.effect(t.id) == "uncertain":
                    self.delivery.confirm(t.id)
                self.trace.emit(
                    "transition_completed", state=self.state, transition=t.id
                )
            raise ValueError("maximum steps exceeded")
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
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            return await self.stop("failed", reason, category)

    def take_control(self, token):
        self.browser.ownership.take(token)
        self.trace.emit(
            "control_transferred",
            ownership="human",
            state=self.state,
            transition=self.transition,
        )

    async def resume(self, token):
        self.browser.ownership.begin_resume(token)
        valid = False
        try:
            kind, screen = await self.observe()
            checkpoints = [
                s
                for s in self.cap.states.values()
                if s.checkpoint and s.screen == screen and kind == "recognized"
            ]
            if len(checkpoints) != 1:
                raise ValueError("no unique permitted checkpoint")
            await self.choose(checkpoints[0].id)
            self.state = checkpoints[0].id
            valid = True
            self.trace.emit(
                "resume_validated",
                state=self.state,
                timing="human_wait",
                duration_s=monotonic() - self.human_started,
            )
        except ValueError as exc:
            self.trace.emit("resume_rejected", reason=str(exc), state=self.state)
        finally:
            self.browser.ownership.finish_resume(valid=valid)
        return valid

    def cancel(self):
        if self.browser.ownership.state not in {"human", "awaiting_human"}:
            raise ValueError("ownership: run is not paused")
        return self.result("cancelled", reason="Operator cancelled")
