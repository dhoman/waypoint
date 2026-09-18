"""The only module that knows Playwright objects; one async session owner."""

import json
from time import monotonic

from playwright.async_api import async_playwright

from waypoint.evidence import sanitized
from waypoint.ownership import Ownership
from waypoint.policy import BrowserPolicy
from waypoint.schema import Action, Inputs, Observation, Target

# Controlled observation implementation, never model/artifact-provided script.
OBSERVE = """() => {
 const visible=e=>!!(e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden';
 const text=e=>(e.innerText||'').trim();
 const fields={};document.querySelectorAll('dt').forEach(e=>{fields[text(e)]=text(e.nextElementSibling)});
 document.querySelectorAll('input:not([type=hidden])').forEach(e=>{if(e.labels?.length)fields['input:'+text(e.labels[0])]=e.value});
 return {
 headings:[...document.querySelectorAll('h1')].filter(visible).map(text), fields,
 controls:[...document.querySelectorAll('button,a,input:not([type=hidden])')].filter(visible).map(e=>({
 role:e.tagName==='A'?'link':e.tagName==='INPUT'?'textbox':'button',
 name:e.getAttribute('aria-label')||(e.labels?.length?text(e.labels[0]):text(e)),
 value:e.tagName==='INPUT'?'[redacted]':null,
 row:e.closest('tr')?text(e.closest('tr')):null
 })),
 tables:[...document.querySelectorAll('table')].filter(visible).map(t=>({
 caption:t.caption?text(t.caption):'',headers:[...t.querySelectorAll('thead th')].map(text),
 rows:[...t.querySelectorAll('tbody tr')].map(r=>[...r.querySelectorAll('td')].map(text))})),
 dialog:[...document.querySelectorAll('dialog[open],[role=dialog]')].some(visible),
 loading:[...document.querySelectorAll('[role=status]')].some(e=>visible(e)&&text(e).includes('Loading')),
 readonly:Object.values(fields).includes('Read-only access'),
 version:document.querySelector('footer')?.innerText.includes('version 1.0')?'1.0':'unknown',
 text:document.querySelector('main')?.innerText.slice(0,6000)||''
 };
}"""


class BrowserSurface:
    capabilities = frozenset({"structural", "screenshots", "manual_events"})

    def __init__(self, url: str, *, headed=False, policy=None):
        self.url = url
        self.headed = headed
        self.policy = policy or BrowserPolicy.for_url(url)
        self.policy.check_url(url)
        self.violation = None
        self.ownership = Ownership()
        self.event_sink = lambda *args, **kwargs: None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=not self.headed)
        self._context = await self._browser.new_context(
            viewport={"width": 1200, "height": 850}, service_workers="block"
        )
        await self._context.route("**/*", self._route)
        await self._context.expose_binding("waypointManualEvent", self._manual_event)
        await self._context.add_init_script("""(() => {
          for (const kind of ['click','input']) document.addEventListener(kind,e=>{
            if (!e.isTrusted) return;
            const t=e.target.closest('button,a,input,textarea,select'); if(!t)return;
            const name=t.tagName==='INPUT'||t.tagName==='TEXTAREA' ? (t.getAttribute('aria-label')||t.labels?.[0]?.innerText||'field') : (t.innerText||'control');
            window.waypointManualEvent({kind,tag:t.tagName,target:name.slice(0,100),value:kind==='input'?'[redacted]':null});
          },true);
        })()""")
        self._page = await self._context.new_page()
        self._context.on("page", self._popup)
        self._page.set_default_timeout(5000)
        await self._page.goto(self.url)
        await (
            self._page.frame_locator('iframe[title="Member workspace"]')
            .get_by_role("heading")
            .first.wait_for()
        )
        return self

    async def __aexit__(self, *_):
        await self._browser.close()
        await self._pw.stop()

    async def _route(self, route):
        try:
            self.policy.check_url(route.request.url)
            if route.request.method != "GET":
                raise ValueError("policy: non-GET request denied")
            await route.continue_()
        except ValueError as exc:
            self.violation = str(exc)
            await route.abort()

    async def _popup(self, page):
        self.violation = "policy: unexpected popup"
        await page.close()

    def _manual_event(self, source, event):
        if self.ownership.state != "human" or source["page"] != self._page:
            return
        self.policy.check_url(source["frame"].url)
        if event.get("kind") in {"click", "input"}:
            self.event_sink(
                "human_action",
                kind=event["kind"],
                tag=str(event.get("tag", ""))[:20],
                target=str(event.get("target", ""))[:100],
                value="[redacted]" if event["kind"] == "input" else None,
                capture="in-page trusted DOM event; not proof of a physical human",
            )

    def _check_session(self):
        if self.violation:
            raise ValueError(self.violation)
        for frame in self._page.frames:
            self.policy.check_url(frame.url)

    async def _frame(self):
        iframe = self._page.locator('iframe[title="Member workspace"]')
        if await iframe.count() != 1:
            raise ValueError("ambiguous or missing application frame")
        return await (await iframe.element_handle()).content_frame()

    async def observe(self) -> Observation:
        self._check_session()
        return Observation.model_validate(await (await self._frame()).evaluate(OBSERVE))

    async def wait_ready(self, timeout_s):
        frame = await self._frame()
        await frame.wait_for_function(
            "() => ![...document.querySelectorAll('[role=status]')].some(e=>e.innerText.includes('Loading'))",
            timeout=timeout_s * 1000,
        )

    async def read(self, target, inputs):
        locator = await self._resolve(target, inputs)
        return await locator.inner_text()

    async def capture(self, directory, name):
        # Only synthetic-local profile is admitted. Masks all form values, including
        # operator notes. This is not a production PII redactor.
        snapshot, screenshot = name + ".json", name + ".png"
        try:
            obs = await self.observe()
            (directory / snapshot).write_text(
                json.dumps(sanitized(obs), indent=2) + "\n"
            )
            frame = await self._frame()
            await self._page.screenshot(
                path=str(directory / screenshot), mask=[frame.locator("input,textarea")]
            )
            return [snapshot, screenshot]
        except Exception:
            (directory / snapshot).write_text(
                json.dumps(
                    {"capture": "unavailable", "policy_violation": self.violation}
                )
            )
            return [snapshot]

    async def _resolve(self, target: Target, inputs: Inputs):
        if target.frame != "Member workspace":
            raise ValueError("unsupported frame")
        scope = await self._frame()
        if target.row_input:
            scope = scope.get_by_role("row").filter(
                has=scope.get_by_role("cell", name=inputs.memberId, exact=True)
            )
        locator = (
            scope.get_by_label(target.name, exact=True)
            if target.by == "label"
            else scope.get_by_role(target.role, name=target.name, exact=True)
        )
        if await locator.count() != 1:
            raise ValueError("ambiguous or missing target")
        return locator

    async def act(self, action: Action, inputs: Inputs):
        self.ownership.require_automation()
        self._check_session()
        obs = await self.observe()
        if obs.dialog or obs.readonly or obs.loading:
            raise ValueError("unsupported blocking state before action")
        for key in ("Member ID", "Search ID"):
            if key in obs.fields and obs.fields[key] != inputs.memberId:
                raise ValueError("identity mismatch before action")
        started = monotonic()
        locator = await self._resolve(action.target, inputs)
        actual = await locator.evaluate(
            """e=>({tag:e.tagName,name:e.name||'',text:(e.innerText||'').trim(),href:e.href||'',method:e.form?.method||'',form_action:e.form?.action||''})"""
        )
        self.policy.check_action(action, actual)
        self.event_sink(
            "target_resolved",
            target=action.target.model_dump(),
            timing="target_resolution",
            duration_s=monotonic() - started,
        )
        self.ownership.require_automation()
        started = monotonic()
        if action.kind == "fill":
            await locator.fill(getattr(inputs, action.input))
        elif action.kind == "click":
            navigates = await locator.evaluate("e => e.tagName === 'A' || !!e.form")
            if navigates:
                async with (await self._frame()).expect_navigation(
                    wait_until="domcontentloaded"
                ):
                    await locator.click()
            else:
                await locator.click()
        else:
            raise ValueError("unsupported surface action")
        self.event_sink(
            "action_delivered",
            kind=action.kind,
            timing="action",
            duration_s=monotonic() - started,
        )
