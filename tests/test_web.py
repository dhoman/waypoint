import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from waypoint.web.browser import Browser
from waypoint.web.schema import Action, Target


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
