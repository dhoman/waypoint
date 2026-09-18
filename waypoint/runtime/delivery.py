"""Delivery and effect are different facts. Uncertainty is sticky until reconciled."""


class DeliveryLedger:
    def __init__(self):
        self._effects = {}

    def effect(self, transition):
        return self._effects.get(transition, "not_attempted")

    async def attempt(self, transition, operation):
        if self.effect(transition) != "not_attempted":
            raise ValueError("retry refused: delivery already attempted")
        # Set before calling the surface, including cancellation and lost replies.
        self._effects[transition] = "uncertain"
        await operation()

    def confirm(self, transition):
        if self.effect(transition) != "uncertain":
            raise ValueError("no attempted effect to confirm")
        self._effects[transition] = "confirmed"
