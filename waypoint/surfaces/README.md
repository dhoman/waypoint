# Surface implementations

- [protocol.py](protocol.py) is the interface discovery/replay consume.
- [browser/session.py](browser/session.py) implements it with Playwright.
- [browser/policy.py](browser/policy.py) owns browser-specific permissions.
- [browser/observe.js](browser/observe.js) is the trusted visible-UI observation
  implementation, not model-generated JavaScript.

Keep a future adapter in `surfaces/<name>/`, including its own policy and target
resolution. Do not subclass the browser to implement another interaction
technology. The [extension guide](../../docs/EXTENDING.md) covers lifecycle,
ownership, evidence, schema changes and required tests.

Only the browser adapter is implemented in production. The in-memory adapter in
`tests/support/` tests the seam; it is not native support. Schema 2 still admits
only browser targets. Supporting another technology requires an explicit tagged
target/scope model as well as an adapter; selectors and artifacts do not become
cross-surface merely because the runner accepts a protocol.
