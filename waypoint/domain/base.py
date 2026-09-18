"""Common model configuration and provenance; independent of any application."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(Model):
    origin: Literal["discovered", "authored", "inferred"]
    note: str
    evidence: list[str] = Field(default_factory=list)
    validated: bool = False
