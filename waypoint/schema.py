"""Closed declarative vocabulary. No artifact-provided code is evaluated."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Inputs(Model):
    memberId: str = Field(pattern=r"^M-[0-9]{3}$")


class Invoice(Model):
    invoice_id: str
    amount: float = Field(ge=0, allow_inf_nan=False)
    status: Literal["Open", "Paid", "Overdue"]


class Summary(Model):
    memberId: str
    currency: Literal["USD"] = "USD"
    invoices: list[Invoice]
    total: float = Field(ge=0, allow_inf_nan=False)


class Target(Model):
    kind: Literal["browser"] = "browser"
    by: Literal["role", "label"]
    name: str = Field(min_length=1, max_length=120)
    role: Literal["button", "link", "textbox"] = "button"
    frame: str = "Member workspace"
    row_input: Literal["memberId"] | None = None


class Predicate(Model):
    op: Literal[
        "heading",
        "field_equals_input",
        "field_equals",
        "input_value",
        "table_present",
        "no_dialog",
    ]
    field: str = ""
    value: str = ""
    input: Literal["memberId"] | None = None

    @model_validator(mode="after")
    def operands(self):
        if self.op in {"field_equals_input", "input_value"} and (
            not self.field or not self.input
        ):
            raise ValueError("binding predicate requires field and input")
        if self.op in {"heading", "table_present"} and not self.value:
            raise ValueError("recognition predicate requires a value")
        if self.op == "field_equals" and not self.field:
            raise ValueError("field predicate requires a field")
        return self


class Action(Model):
    kind: Literal["fill", "click", "extract", "outcome"]
    target: Target | None = None
    input: Literal["memberId"] | None = None

    @model_validator(mode="after")
    def shape(self):
        if self.kind in {"fill", "click"} and self.target is None:
            raise ValueError("UI action requires target")
        if self.kind == "fill" and self.input is None:
            raise ValueError("fill requires explicit input binding")
        return self


class Provenance(Model):
    origin: Literal["discovered", "authored", "inferred"]
    note: str
    evidence: list[str] = Field(default_factory=list)
    validated: bool = False


class Screen(Model):
    id: str
    recognition: list[Predicate] = Field(min_length=1)
    identity: Predicate | None = None
    controls: dict[str, Target] = Field(default_factory=dict)
    fields: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=lambda: ["dialog", "Read-only access"])
    variants: list[str] = Field(default_factory=list)
    provenance: Provenance


class State(Model):
    id: str
    screen: str | None = None
    progress: Literal[
        "search", "query_bound", "results", "identity_verified", "invoices", "terminal"
    ]
    outcome: Literal["succeeded", "member_not_found"] | None = None
    checkpoint: bool = False


class Transition(Model):
    id: str
    source: str
    destination: str
    alternatives: dict[str, list[Predicate]] = Field(default_factory=dict)
    action: Action
    guards: list[Predicate] = Field(default_factory=list)
    postconditions: list[Predicate] = Field(default_factory=list)
    risk: Literal["read", "navigation", "write"] = "read"
    timeout_s: float = Field(default=5, gt=0, le=30)
    retries: Literal[0] = 0
    retry_safe: bool = False
    recovery: Literal["wait_loading_then_check", "stop"] = "wait_loading_then_check"
    provenance: Provenance

    @model_validator(mode="after")
    def safe_retry(self):
        if self.retries and (not self.retry_safe or self.risk == "write"):
            raise ValueError("unsafe retry")
        return self


class Capability(Model):
    schema_version: Literal["1.0"] = "1.0"
    capability_id: str = "member-invoice-summary"
    revision: int = Field(default=1, ge=1)
    description: str
    surface: Literal["browser"] = "browser"
    app: Literal["Member Console"] = "Member Console"
    app_version: Literal["1.0"] = "1.0"
    profile: Literal["synthetic-local"] = "synthetic-local"
    required_inputs: dict[str, Literal["member_id"]] = Field(
        default_factory=lambda: {"memberId": "member_id"}
    )
    output_type: Literal["invoice_summary"] = "invoice_summary"
    entry: str
    screens: dict[str, Screen]
    states: dict[str, State]
    transitions: list[Transition]
    terminals: list[str]
    max_steps: int = Field(default=20, ge=1, le=100)
    max_visits: int = Field(default=2, ge=1, le=5)
    discovery_run: str
    provider: str
    model: str
    compiler: str = "waypoint-0.1.0"
    amendments: list[str] = Field(default_factory=list)
    status: Literal["draft", "validated"] = "draft"
    validation_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def graph(self):
        if self.required_inputs != {"memberId": "member_id"}:
            raise ValueError("unsupported input contract")
        if self.entry not in self.states or not self.terminals:
            raise ValueError("missing entry or terminals")
        for key, s in self.screens.items():
            if key != s.id:
                raise ValueError("screen key mismatch")
        for key, s in self.states.items():
            if key != s.id or (s.screen is not None and s.screen not in self.screens):
                raise ValueError("invalid state/screen reference")
            if not s.outcome and s.screen is None:
                raise ValueError("nonterminal state requires a recognized screen")
        ids = set()
        reachable = {self.entry}
        for t in self.transitions:
            if (
                t.id in ids
                or t.source not in self.states
                or t.destination not in self.states
            ):
                raise ValueError("duplicate transition or missing target")
            ids.add(t.id)
            if any(dest not in self.states for dest in t.alternatives):
                raise ValueError("missing alternative target")
            if self.states[t.source].outcome:
                raise ValueError("terminal has outgoing transition")
        for _ in self.states:
            reachable.update(
                t.destination for t in self.transitions if t.source in reachable
            )
            reachable.update(
                dest
                for t in self.transitions
                if t.source in reachable
                for dest in t.alternatives
            )
        if set(self.states) != reachable:
            raise ValueError("unreachable state")
        for terminal in self.terminals:
            if terminal not in reachable or not self.states[terminal].outcome:
                raise ValueError("unreachable or invalid required terminal")
        if {s.id for s in self.states.values() if s.outcome} != set(self.terminals):
            raise ValueError("terminal declarations disagree")
        # All cycles are globally bounded by max_steps and max_visits. No executable
        # expression, unbounded loop or precedence language is supported.
        if self.status == "validated" and not self.validation_evidence:
            raise ValueError("validation needs evidence")
        return self


class Observation(Model):
    headings: list[str] = Field(default_factory=list)
    fields: dict[str, str] = Field(default_factory=dict)
    controls: list[dict] = Field(default_factory=list)
    tables: list[dict] = Field(default_factory=list)
    dialog: bool = False
    loading: bool = False
    readonly: bool = False
    version: str = ""
    text: str = ""


class Result(Model):
    run_id: str
    capability_id: str
    revision: int
    status: Literal[
        "succeeded", "business_outcome", "awaiting_intervention", "failed", "cancelled"
    ]
    outputs: Summary | None = None
    business_code: str | None = None
    state: str
    transition: str | None = None
    failure_category: str | None = None
    reason: str | None = None
    expected: list[str] = Field(default_factory=list)
    expected_facts: dict[str, str] = Field(default_factory=dict)
    observed: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    effect: Literal["not_attempted", "confirmed", "uncertain"] = "not_attempted"


def screen_id(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")
