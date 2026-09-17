"""Developer-owned synthetic fixture. Never imported by discovery or replay."""

import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

MEMBERS = {
    "M-101": (
        "Ada Mercer",
        [["INV-1011", "120.00", "Paid"], ["INV-1012", "45.50", "Overdue"]],
    ),
    "M-202": (
        "Ben Ortiz",
        [["INV-2021", "84.25", "Open"], ["INV-2022", "15.75", "Paid"]],
    ),
}
STYLE = """body{font:16px Georgia;background:#eeeee7;color:#263339;margin:30px}
header{background:#243a46;color:white;padding:16px}main{background:white;padding:24px;border:1px solid #aaa}
table{border-collapse:collapse;min-width:600px;margin:20px 0}td,th{padding:12px;border:1px solid #aab;text-align:left}
button,input{font:inherit;padding:8px}a{color:#065a81}dt{font-weight:bold;float:left;width:120px}dd{margin:12px 0 12px 140px}
iframe{width:100%;height:690px;border:0}dialog{border:3px solid #b66;max-width:440px}footer{margin:20px;color:#657}
"""


def document(body):
    return f'<!doctype html><html><head><meta charset="utf-8"><title>Member Console</title><style>{STYLE}</style></head><body>{body}<footer>Member Console · version 1.0 · Synthetic demonstration data</footer></body></html>'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        member = query.get("memberId", [""])[0]
        scenario = query.get("scenario", ["normal"])[0]
        if scenario not in {
            "normal",
            "slow",
            "dialog",
            "mismatch",
            "ambiguous",
            "readonly",
        }:
            scenario = "normal"
        esc = html.escape

        def link(route, **params):
            return esc(
                route + "?" + urlencode({"scenario": scenario, **params}), quote=True
            )

        if parsed.path == "/":
            body = f'<header><h1>Northstar Membership / Operations</h1></header><iframe title="Member workspace" src="{link("/search")}"></iframe>'
        elif parsed.path == "/search":
            body = f'<main><h1>Member search</h1><form action="/results" method="get"><label for="member">Member ID</label> <input id="member" name="memberId" required pattern="M-[0-9]{{3}}"><input type="hidden" name="scenario" value="{scenario}"> <button>Search</button></form></main>'
        elif parsed.path == "/results":
            if member not in MEMBERS:
                body = f"<main><h1>No members found</h1><dl><dt>Search ID</dt><dd>{esc(member)}</dd></dl></main>"
            else:
                row = f'<tr><td>{esc(member)}</td><td>{MEMBERS[member][0]}</td><td><a href="{link("/profile", memberId=member)}">View profile</a></td></tr>'
                body = f"<main><h1>Search results</h1><dl><dt>Search ID</dt><dd>{esc(member)}</dd></dl><table><caption>Members</caption><thead><tr><th>Member ID</th><th>Name</th><th>Details</th></tr></thead><tbody>{row * (2 if scenario == 'ambiguous' else 1)}</tbody></table></main>"
        elif parsed.path in {"/profile", "/invoices"} and member in MEMBERS:
            shown = "M-101" if scenario == "mismatch" else member
            name, invoices = MEMBERS[shown]
            fields = f"<dl><dt>Member ID</dt><dd>{shown}</dd><dt>Name</dt><dd>{name}</dd><dt>Access</dt><dd>{'Read-only access' if scenario == 'readonly' else 'Standard'}</dd></dl>"
            if parsed.path == "/profile":
                body = f"<main><h1>Member profile</h1>{fields}<a href=\"{link('/invoices', memberId=shown)}\">Invoices</a> <button onclick=\"document.querySelector('output').textContent='Account closed'\">Close account</button><output></output></main>"
                if scenario == "dialog":
                    body += '<dialog open><h2>Operator notice</h2><p>Acknowledge the archive maintenance notice to continue.</p><label>Operator note <input aria-label="Operator note"></label><button onclick="this.closest(\'dialog\').remove()">Dismiss notice</button></dialog>'
            else:
                rows = "".join(
                    "<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>"
                    for row in invoices
                )
                content = f"<h1>Member invoices</h1>{fields}<table><caption>Invoice ledger</caption><thead><tr><th>Invoice</th><th>Amount USD</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>"
                body = f"<main>{content}</main>"
                if scenario == "slow":
                    body = (
                        '<main><h1>Loading invoices</h1><p role="status">Loading…</p></main><script>setTimeout(()=>document.querySelector("main").innerHTML='
                        + json.dumps(content)
                        + ",1200)</script>"
                    )
        else:
            self.send_error(404)
            return
        payload = document(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class FixtureServer:
    def __init__(self, port=0):
        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/"

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
