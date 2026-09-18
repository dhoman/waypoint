"""Optional OpenAI provider. No import path from strict replay."""

import json
import os

from openai import AsyncOpenAI


class OpenAIProvider:
    name = "openai"

    def __init__(self, model, *, decision_type, instructions):
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("Set OPENAI_API_KEY for discovery")
        if not model:
            raise ValueError("Set WAYPOINT_MODEL or pass --model")
        self.model = model
        self.decision_type = decision_type
        self.instructions = instructions
        self.client = AsyncOpenAI(timeout=40, max_retries=0)

    async def decide(self, goal, inputs, observation, history):
        response = await self.client.responses.parse(
            model=self.model,
            instructions=self.instructions,
            input=json.dumps(
                {
                    "goal": goal,
                    "input_bindings": inputs.model_dump()
                    if hasattr(inputs, "model_dump")
                    else inputs,
                    "untrusted_ui": observation.model_dump(),
                    "previous_actions": history,
                }
            ),
            text_format=self.decision_type,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("provider did not return an allowed decision")
        return response.output_parsed
