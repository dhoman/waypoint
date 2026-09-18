"""Typed model decisions and the provider seam; no SDK or browser imports."""

from typing import Literal, Protocol

from pydantic import Field

from waypoint.domain.artifact import Extraction, Observation, Predicate, Target
from waypoint.domain.base import Model


class ScreenProposal(Model):
    id: str
    recognition: list[Predicate] = Field(min_length=1)
    identity: list[Predicate] = Field(default_factory=list)


class Decision(Model):
    operation: Literal["click", "fill", "select", "press", "check", "wait", "finish"]
    target: Target | None = None
    input: str | None = None
    value: str | None = None
    screen: ScreenProposal
    outputs: list[Extraction] = Field(default_factory=list)
    rationale: str = Field(max_length=240)


class Provider(Protocol):
    name: str
    model: str

    async def decide(
        self, goal: str, inputs: dict, observation: Observation, history: list[dict]
    ) -> Decision: ...
