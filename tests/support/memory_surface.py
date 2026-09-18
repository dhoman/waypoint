"""Test-only surface adapter. No browser objects, URLs, SDKs or native claims."""

from waypoint.runtime.ownership import Ownership
from waypoint.surfaces.protocol import SurfaceBinding


class MemorySurface:
    capabilities = frozenset({"structural"})

    def __init__(self, observations, actions=(), *, scope="memory:test"):
        self.observations = observations
        self.actions = list(actions)
        self.scope = scope
        self.binding = SurfaceBinding(scope, "/")
        self.position = 0
        self.ownership = Ownership()
        self.event_sink = lambda *args, **kwargs: None
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    def validate_capability(self, capability):
        if capability.surface != "browser" or capability.origin != self.scope:
            raise ValueError("policy: capability belongs to another surface scope")

    async def observe(self):
        return self.observations[self.position].model_copy(deep=True)

    async def resolve(self, target, inputs):
        return {"unique": True, "visible": True}

    async def act(self, action, inputs):
        self.ownership.require_automation()
        if self.position >= len(self.actions) or action != self.actions[self.position]:
            raise ValueError("policy: test adapter refuses unapproved action")
        self.position += 1

    async def read(self, target, inputs, attribute="text"):
        return (await self.observe()).fields[target.name]

    async def read_rows(self, target, columns, inputs, limit):
        raise ValueError("unsupported collection in memory test adapter")

    async def settle(self, timeout_s=5):
        pass

    async def capture(self, directory, name):
        return []
