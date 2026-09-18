import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from waypoint.web.browser import Browser
from waypoint.web.schema import Action, Target


async def test_unknown_model_predicate_binding_is_rejected_before_browser_access():
    from waypoint.web.interpret import holds
    from waypoint.web.schema import Observation, Predicate

    with pytest.raises(ValueError, match="unknown predicate input"):
        await holds(
            Predicate(op="heading_input", input="invented"), Observation(), {}, None
        )


async def test_generic_identity_and_ambiguous_recognition_fail_closed():
    from waypoint.web.interpret import recognize
    from waypoint.web.schema import Observation, Predicate, Screen

    screen = Screen(
        id="details",
        recognition=[Predicate(op="heading", value="Details")],
        identity=[Predicate(op="field_equals_input", field="Account", input="account")],
    )
    obs = Observation(headings=["Details"], fields={"Account": "wrong"})
    with pytest.raises(ValueError, match="identity"):
        await recognize({"details": screen}, obs, {"account": "wanted"}, None)
    obs.fields["Account"] = "wanted"
    kind, _, _ = await recognize(
        {"one": screen, "two": screen}, obs, {"account": "wanted"}, None
    )
    assert kind == "ambiguous"


def test_discovery_separates_entity_predicate_from_screen_type():
    from waypoint.web.discovery import Decision, ScreenProposal, parameterize
    from waypoint.web.schema import Observation, Predicate

    binding = Predicate(op="field_equals_input", field="Account", input="account")
    decision = Decision(
        operation="wait",
        rationale="test",
        screen=ScreenProposal(
            id="details",
            recognition=[Predicate(op="heading", value="Details"), binding],
        ),
    )
    screen = parameterize(
        decision,
        Observation(headings=["Details"], fields={"Account": "A"}),
        {"account": "A"},
    )
    assert screen.recognition == [Predicate(op="heading", value="Details")]
    assert screen.identity == [binding]


def test_generic_policy_does_not_treat_arbitrary_click_as_readonly():
    from waypoint.web.policy import Policy

    policy = Policy.for_url("https://example.com/")
    action = Action(
        kind="click", target=Target(by="role", role="button", name="Delete part")
    )
    with pytest.raises(ValueError, match="consequential"):
        policy.check_action(action, {"label": "Delete part"})
    with pytest.raises(ValueError, match="origin"):
        policy.check_action(
            action, {"label": "Documentation", "href": "https://outside.example/"}
        )
    with pytest.raises(ValueError, match="unclassified"):
        policy.check_action(action, {"label": "Do something"})
    assert not policy.request_allowed("https://example.com/api", "POST", "fetch")


class CatalogHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        body = """<!doctype html><html><title>Workshop catalog</title><body>
        <h1>Workshop catalog</h1><form action="/lookup" method="get">
        <label>Part number <input name="part"></label><button>Search parts</button>
        </form></body></html>"""
        if self.path.startswith("/lookup"):
            from urllib.parse import parse_qs, urlsplit

            part = parse_qs(urlsplit(self.path).query).get("part", [""])[0]
            price = "19.75" if part == "B-22" else "7.25"
            body = f"""<!doctype html><html><title>Part details</title><body>
            <h1>Part details</h1><dl><dt>Part number</dt><dd>{part}</dd>
            <dt>Price</dt><dd>{price}</dd></dl><button>Delete part</button></body></html>"""
        payload = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class CatalogServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), CatalogHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/"
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


async def test_unrelated_top_level_site_accepts_arbitrary_input_without_site_code():
    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            obs = await browser.observe()
            assert "Workshop catalog" in obs.headings
            await browser.act(
                Action(
                    kind="fill",
                    target=Target(by="label", name="Part number"),
                    input="part",
                ),
                {"part": "B-22"},
            )
            await browser.act(
                Action(
                    kind="click",
                    target=Target(by="role", role="button", name="Search parts"),
                ),
                {"part": "B-22"},
            )
            observed = await browser.observe()
            assert observed.fields == {"Part number": "B-22", "Price": "19.75"}


async def test_generic_adapter_synchronizes_iframe_navigation():
    from waypoint.fixture import FixtureServer

    with FixtureServer() as app:
        async with Browser(app.url) as browser:
            inputs = {"entity": "M-202"}
            for kind, target, binding in [
                (
                    "fill",
                    Target(by="label", name="Member ID", frame="Member workspace"),
                    "entity",
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="button",
                        name="Search",
                        frame="Member workspace",
                    ),
                    None,
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="link",
                        name="View profile",
                        row_input="entity",
                        frame="Member workspace",
                    ),
                    None,
                ),
                (
                    "click",
                    Target(
                        by="role",
                        role="link",
                        name="Invoices",
                        frame="Member workspace",
                    ),
                    None,
                ),
            ]:
                await browser.act(
                    Action(kind=kind, target=target, input=binding), inputs
                )
            observed = await browser.observe()
            assert "Member invoices" in observed.headings
            assert observed.fields["Member ID"] == "M-202"


async def test_generic_compiled_extraction_replays_new_input(tmp_path):
    from waypoint.evidence import Trace
    from waypoint.web.compiler import compile_route
    from waypoint.web.runtime import Replay
    from waypoint.web.schema import Extraction, Predicate, Screen

    inputs = {"part": "A-11"}
    search = Screen(
        id="catalog", recognition=[Predicate(op="heading", value="Workshop catalog")]
    )
    details = Screen(
        id="details",
        recognition=[Predicate(op="heading", value="Part details")],
        identity=[
            Predicate(op="field_equals_input", field="Part number", input="part")
        ],
    )
    actions = [
        Action(
            kind="fill", target=Target(by="label", name="Part number"), input="part"
        ),
        Action(
            kind="click", target=Target(by="role", role="button", name="Search parts")
        ),
    ]
    output = [
        Extraction(name="part", source="field", field="Part number"),
        Extraction(name="price", source="field", field="Price", value_type="number"),
    ]
    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            observations = [await browser.observe()]
            for action in actions:
                await browser.act(action, inputs)
                observations.append(await browser.observe())
        cap = compile_route(
            observations,
            actions,
            [search, search, details],
            output,
            inputs=inputs,
            goal="Find a part and read its price",
            url=app.url,
            run_id="test",
            provider="test",
            model="none",
        )
        async with Browser(app.url) as browser:
            result = await Replay(
                cap, browser, {"part": "B-22"}, Trace(tmp_path, cap)
            ).run()
    assert result.status == "succeeded"
    assert result.outputs == {"part": "B-22", "price": 19.75}


async def test_generic_discovery_validates_model_proposed_outputs(tmp_path):
    from waypoint.evidence import Trace
    from waypoint.web.discovery import Decision, ScreenProposal, discover
    from waypoint.web.schema import Extraction, Predicate

    class Provider:
        name = "test"
        model = "fabricated"

        async def decide(self, goal, inputs, observation, history):
            return Decision(
                operation="finish",
                screen=ScreenProposal(
                    id="catalog",
                    recognition=[Predicate(op="heading", value="Workshop catalog")],
                ),
                outputs=[Extraction(name="price", source="field", field="nonexistent")],
                rationale="A test-only invalid output rule",
            )

    with CatalogServer() as app:
        async with Browser(app.url) as browser:
            cap = await discover(
                "Read a price", browser, {}, Provider(), Trace(tmp_path, kind="test")
            )
    assert cap is None
    assert not (tmp_path / "capability.json").exists()
    assert "output field missing" in (tmp_path / "events.jsonl").read_text()
    assert "no_progress" in (tmp_path / "result.json").read_text()
