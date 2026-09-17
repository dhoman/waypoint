"""Runtime-owned allowlist, independent of model and artifact risk labels."""

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from waypoint.schema import Action


@dataclass(frozen=True)
class BrowserPolicy:
    origin: str
    routes: frozenset[str] = frozenset(
        {"/", "/search", "/results", "/profile", "/invoices"}
    )
    click_names: frozenset[str] = frozenset({"Search", "View profile", "Invoices"})

    @classmethod
    def for_url(cls, url):
        parsed = urlsplit(url)
        if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.scheme != "http":
            raise ValueError("policy: only local synthetic HTTP targets are supported")
        return cls(f"{parsed.scheme}://{parsed.netloc}")

    def check_url(self, url):
        p = urlsplit(url)
        if f"{p.scheme}://{p.netloc}" != self.origin or p.path not in self.routes:
            raise ValueError("policy: origin or route denied")
        if (
            p.username
            or p.password
            or p.fragment
            or set(parse_qs(p.query)) - {"scenario", "memberId"}
        ):
            raise ValueError("policy: unsupported URL configuration")

    def check_action(self, action: Action, actual: dict):
        if action.target is None:
            raise ValueError("policy: missing UI target")
        if action.kind == "fill":
            if (
                actual["tag"] != "INPUT"
                or actual["name"] != "memberId"
                or action.target.name != "Member ID"
            ):
                raise ValueError("policy: field denied")
        elif action.kind == "click":
            if actual["text"] not in self.click_names:
                raise ValueError("policy: consequential or unknown control denied")
            if actual["tag"] == "A":
                self.check_url(actual["href"])
                allowed = {"View profile": "/profile", "Invoices": "/invoices"}
                if urlsplit(actual["href"]).path != allowed.get(actual["text"]):
                    raise ValueError("policy: link semantics changed")
            elif actual["tag"] == "BUTTON":
                if actual["text"] != "Search" or actual["method"] != "get":
                    raise ValueError("policy: form denied")
                self.check_url(actual["form_action"])
                if urlsplit(actual["form_action"]).path != "/results":
                    raise ValueError("policy: form destination denied")
            else:
                raise ValueError("policy: control type denied")
        else:
            raise ValueError("policy: action denied")
