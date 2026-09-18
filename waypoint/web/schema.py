from typing import Literal

from pydantic import Field, model_validator

from waypoint.schema import Model, Provenance

Scalar = str | int | float | bool


class Target(Model):
    kind: Literal["browser"] = "browser"
    by: Literal["role", "label", "text", "title", "placeholder", "css"]
    name: str = ""
    role: str = ""
    frame: str = ""  # Empty means main document; otherwise an exact frame name/title.
    name_input: str | None = None
    row_input: str | None = None


class Action(Model):
    kind: Literal["click", "fill", "select", "press", "check", "extract", "outcome"]
    target: Target | None = None
    input: str | None = None
    value: str | None = None

    @model_validator(mode="after")
    def valid(self):
        if self.kind not in {"extract", "outcome"} and self.target is None:
            raise ValueError("action requires a target")
        if (
            self.kind in {"fill", "select"}
            and self.input is None
            and self.value is None
        ):
            raise ValueError("fill/select needs a binding or literal value")
        if self.kind == "press" and self.value not in {
            "Enter",
            "Tab",
            "Escape",
            "ArrowDown",
            "ArrowUp",
        }:
            raise ValueError("unsupported key")
        return self


class Observation(Model):
    title: str = ""
    headings: list[str] = Field(default_factory=list)
    fields: dict[str, str] = Field(default_factory=dict)
    controls: list[dict] = Field(default_factory=list)
    tables: list[dict] = Field(default_factory=list)
    frames: list[str] = Field(default_factory=list)
    dialog: bool = False
    loading: bool = False
    text: str = ""
    structure: str = ""


class Predicate(Model):
    op: Literal[
        "heading",
        "heading_input",
        "title",
        "text_present",
        "field_equals_input",
        "field_equals",
        "target_present",
        "target_text_input",
        "no_dialog",
        "table_present",
    ]
    value: str = ""
    field: str = ""
    input: str | None = None
    target: Target | None = None

    @model_validator(mode="after")
    def operands(self):
        if (
            self.op in {"heading_input", "field_equals_input", "target_text_input"}
            and not self.input
        ):
            raise ValueError("predicate requires input binding")
        if self.op.startswith("target_") and self.target is None:
            raise ValueError("predicate requires a target")
        if self.op.startswith("field_") and not self.field:
            raise ValueError("predicate requires a field")
        if (
            self.op in {"heading", "title", "text_present", "table_present"}
            and not self.value
        ):
            raise ValueError("predicate requires a value")
        return self


class Column(Model):
    name: str
    target: Target | None = None  # relative to a repeated list item
    field: str = ""  # table column header
    attribute: Literal["text", "href", "title"] = "text"
    value_type: Literal["string", "number", "boolean"] = "string"


class Extraction(Model):
    name: str
    source: Literal["field", "text", "attribute", "list", "table", "input", "sum"]
    field: str = ""
    target: Target | None = None
    attribute: Literal["text", "href", "title"] = "text"
    value_type: Literal["string", "number", "boolean"] = "string"
    columns: list[Column] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def operands(self):
        if self.source in {"text", "attribute", "list"} and self.target is None:
            raise ValueError("extraction requires target")
        if self.source in {"field", "table", "input", "sum"} and not self.field:
            raise ValueError("extraction requires field/reference")
        if self.source in {"list", "table"} and not self.columns:
            raise ValueError("collection requires typed columns")
        return self


class Screen(Model):
    id: str
    recognition: list[Predicate] = Field(min_length=1)
    identity: list[Predicate] = Field(default_factory=list)
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(
            origin="discovered",
            note="Proposed from observed UI; replay validation pending",
        )
    )


class State(Model):
    id: str
    screen: str | None = None
    progress: str
    outcome: str | None = None
    checkpoint: bool = False


class Transition(Model):
    id: str
    source: str
    destination: str
    action: Action
    guards: list[Predicate] = Field(default_factory=list)
    postconditions: list[Predicate] = Field(default_factory=list)
    timeout_s: float = Field(default=10, gt=0, le=60)
    risk: Literal["read", "navigation", "requires_permission"] = "read"
    retries: Literal[0] = 0
    alternatives: dict[str, list[Predicate]] = Field(default_factory=dict)
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(
            origin="discovered", note="Observed action; no inferred reverse edge"
        )
    )


class Capability(Model):
    schema_version: Literal["2.0"] = "2.0"
    capability_id: str
    revision: int = Field(default=1, ge=1)
    description: str
    surface: Literal["browser"] = "browser"
    app: str
    app_version: str = "unasserted"
    origin: str
    entry_path: str
    required_inputs: dict[str, Literal["string", "number", "boolean"]]
    output: list[Extraction] = Field(min_length=1)
    entry: str
    screens: dict[str, Screen]
    states: dict[str, State]
    transitions: list[Transition]
    terminals: list[str]
    max_steps: int = Field(default=40, ge=1, le=200)
    discovery_run: str
    provider: str
    model: str
    compiler: str = "waypoint-web-2"
    status: Literal["draft", "validated"] = "draft"
    validation_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def graph(self):
        if self.entry not in self.states or not self.terminals:
            raise ValueError("missing entry/terminals")
        for key, state in self.states.items():
            if state.id != key or (
                not state.outcome and state.screen not in self.screens
            ):
                raise ValueError("missing screen")
        for key, screen in self.screens.items():
            if key != screen.id or all(p.op == "no_dialog" for p in screen.recognition):
                raise ValueError("screen requires meaningful recognition")
        transition_ids = set()
        reachable = {self.entry}
        for t in self.transitions:
            if (
                t.id in transition_ids
                or t.source not in self.states
                or t.destination not in self.states
                or any(d not in self.states for d in t.alternatives)
            ):
                raise ValueError("invalid transition reference")
            if self.states[t.source].outcome:
                raise ValueError("terminal has outgoing transition")
            transition_ids.add(t.id)
        for _ in self.states:
            reachable.update(
                t.destination for t in self.transitions if t.source in reachable
            )
            reachable.update(
                d
                for t in self.transitions
                if t.source in reachable
                for d in t.alternatives
            )
        if reachable != set(self.states) or set(self.terminals) != {
            s.id for s in self.states.values() if s.outcome
        }:
            raise ValueError("unreachable or invalid terminal")

        # Runtime bounds all control flow; actions are never redelivered after uncertainty.
        def refs(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if (
                        key in {"input", "name_input", "row_input"}
                        and item is not None
                        and item not in self.required_inputs
                    ):
                        raise ValueError("invalid input reference")
                    refs(item)
            elif isinstance(value, list):
                for item in value:
                    refs(item)

        refs([s.model_dump() for s in self.screens.values()])
        refs([t.model_dump() for t in self.transitions])
        refs([o.model_dump() for o in self.output])
        names = set()
        for output in self.output:
            if output.name in names:
                raise ValueError("duplicate output name")
            if output.source == "input" and output.field not in self.required_inputs:
                raise ValueError("invalid output input binding")
            if output.source == "sum" and output.field.split(".")[0] not in names:
                raise ValueError("sum requires an earlier output")
            names.add(output.name)
        return self

    def validate_inputs(self, inputs):
        if set(inputs) != set(self.required_inputs):
            raise ValueError("missing or unexpected required inputs")
        for key, kind in self.required_inputs.items():
            value = inputs[key]
            if (
                kind == "string"
                and not isinstance(value, str)
                or kind == "boolean"
                and not isinstance(value, bool)
                or kind == "number"
                and (isinstance(value, bool) or not isinstance(value, (int, float)))
            ):
                raise ValueError("input type mismatch: " + key)
        return inputs


class Result(Model):
    run_id: str
    capability_id: str
    revision: int
    status: Literal[
        "succeeded", "business_outcome", "awaiting_intervention", "failed", "cancelled"
    ]
    state: str
    transition: str | None = None
    outputs: dict | None = None
    business_code: str | None = None
    failure_category: str | None = None
    reason: str | None = None
    expected: list[str] = Field(default_factory=list)
    observed: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
