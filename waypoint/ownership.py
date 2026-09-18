"""Single-owner session lease. Resume validates before automation is re-enabled."""

import secrets


class Ownership:
    def __init__(self):
        self.state = "automation"
        self.token = None

    def require_automation(self):
        if self.state != "automation":
            raise ValueError(
                f"ownership: automated actions prohibited during {self.state}"
            )

    def request(self):
        self.require_automation()
        self.state = "awaiting_human"
        self.token = secrets.token_hex(6)
        return self.token

    def _check(self, token, state):
        if token != self.token or self.state != state or token is None:
            raise ValueError("ownership: stale or duplicate control command")

    def take(self, token):
        self._check(token, "awaiting_human")
        self.state = "human"

    def begin_resume(self, token):
        self._check(token, "human")
        self.state = "validating_resume"

    def finish_resume(self, *, valid):
        if self.state != "validating_resume":
            raise ValueError("ownership: no pending resume")
        self.state = "automation" if valid else "human"
        if valid:
            self.token = None

    def terminate(self):
        self.state = "terminal"
        self.token = None
