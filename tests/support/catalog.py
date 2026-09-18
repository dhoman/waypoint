import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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
