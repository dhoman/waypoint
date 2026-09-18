"""The execution seam: values in/out, never a Page, Locator or native handle.

Adapters satisfy this protocol structurally; they do not subclass a browser.
The owner opens one session with `async with`, then discovery/replay borrows it.
See docs/EXTENDING.md for invariants that Python signatures cannot enforce.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, TypedDict

from waypoint.domain.artifact import (
    Action,
    Capability,
    Column,
    Observation,
    Scalar,
    Target,
)
from waypoint.runtime.ownership import Ownership


class Resolution(TypedDict):
    unique: bool
    visible: bool


@dataclass(frozen=True)
class SurfaceBinding:
    """Adapter-supplied artifact scope. Schema 2 currently supports browser scopes."""

    origin: str
    entry_path: str
    surface: str = "browser"


class Surface(Protocol):
    binding: SurfaceBinding
    capabilities: frozenset[str]
    ownership: Ownership
    event_sink: Callable[..., None]

    async def __aenter__(self) -> "Surface": ...
    async def __aexit__(self, *args) -> None: ...
    def validate_capability(self, capability: Capability) -> None:
        """Reject unsupported surface/target scope before any artifact action."""
        ...

    async def observe(self) -> Observation: ...
    async def resolve(
        self, target: Target, inputs: dict[str, Scalar]
    ) -> Resolution: ...
    async def act(self, action: Action, inputs: dict[str, Scalar]) -> None:
        """Check ownership, identity-relevant UI, policy and uniqueness before delivery."""
        ...

    async def read(
        self, target: Target, inputs: dict[str, Scalar], attribute: str = "text"
    ) -> str: ...
    async def read_rows(
        self,
        target: Target,
        columns: list[Column],
        inputs: dict[str, Scalar],
        limit: int,
    ) -> list[dict[str, str]]: ...
    async def settle(self, timeout_s: float = 5) -> None:
        """Bound readiness by a deadline; do not retry delivered actions."""
        ...

    async def capture(self, directory: Path, name: str) -> list[str]: ...
