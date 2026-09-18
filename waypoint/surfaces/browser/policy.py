"""Generic browser permission policy; no application names or workflow paths."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def origin(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("policy: expected an HTTP(S) URL without credentials")
    return f"{parsed.scheme}://{parsed.netloc}"


@dataclass
class Policy:
    origins: set[str]
    allowed_controls: set[str] = field(default_factory=set)
    allowed_methods: set[str] = field(
        default_factory=lambda: {"GET", "HEAD", "OPTIONS"}
    )

    @classmethod
    def for_url(
        cls, url, *, allowed_origins=(), allowed_controls=(), allowed_methods=()
    ):
        return cls(
            {origin(url), *(origin(u) for u in allowed_origins)},
            set(allowed_controls),
            {"GET", "HEAD", "OPTIONS", *(m.upper() for m in allowed_methods)},
        )

    def check_url(self, url):
        if origin(url) not in self.origins:
            raise ValueError(
                "policy: navigation origin not authorized; use --allow-origin"
            )

    def request_allowed(self, url, method, resource_type):
        try:
            resource_origin = origin(url)
        except ValueError:
            return False
        # Passive asset delivery does not grant navigation or interaction authority.
        if (
            resource_type in {"image", "stylesheet", "font", "script", "media"}
            and method == "GET"
        ):
            return True
        return resource_origin in self.origins and method in self.allowed_methods

    def check_action(self, action, facts):
        label = facts["label"]
        if facts.get("password") or facts.get("file"):
            raise ValueError("policy: secret/file fields require manual entry")
        if label in self.allowed_controls:
            return
        if re.search(
            r"\b(delete|remove|purchase|buy|pay|send|publish|transfer|unsubscribe|sign.?out|log.?out|close account|save|create|register)\b",
            label,
            re.I,
        ):
            raise ValueError("policy: consequential control requires --allow-control")
        if action.kind in {"fill", "select"}:
            return
        if action.kind == "press" and action.value != "Enter":
            return
        if facts.get("href"):
            self.check_url(facts["href"])
            if re.search(
                r"/(delete|remove|logout|signout|purchase|checkout)(/|\?|$)",
                facts["href"],
                re.I,
            ):
                raise ValueError("policy: consequential navigation denied")
            return
        if facts.get("form_method") == "get":
            self.check_url(facts["form_action"])
            return
        if (
            facts.get("role") in {"tab", "menuitem"}
            or facts.get("expanded") is not None
        ):
            return
        if re.match(
            r"^(search|find|look\s?up|filter|next|previous|back|open|view|show|browse|menu|expand|more|accept cookies|reject cookies)\b",
            label,
            re.I,
        ):
            return
        raise ValueError(
            "policy: unclassified control; authorize its exact label with --allow-control"
        )
