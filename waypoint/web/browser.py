"""Generic structural browser adapter. All site knowledge comes from the UI."""

import json
from pathlib import Path
from time import monotonic

from playwright.async_api import Error as BrowserError
from playwright.async_api import async_playwright

from waypoint.evidence import sanitize_manual_event
from waypoint.ownership import Ownership
from waypoint.web.policy import Policy
from waypoint.web.schema import Observation, Target

OBSERVE = Path(__file__).with_name("observe.js").read_text()


class Browser:
    capabilities = frozenset({"structural", "screenshots", "manual_events"})

    def __init__(self, url, *, headed=False, policy=None):
        self.url, self.headed = url, headed
        self.policy = policy or Policy.for_url(url)
        self.policy.check_url(url)
        self.ownership = Ownership()
        self.event_sink = lambda *args, **kwargs: None
        self.violation = None

    async def __aenter__(self):
        self.pw = await async_playwright().start()
        try:
            self.browser = await self.pw.chromium.launch(headless=not self.headed)
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 900}, service_workers="block"
            )
            await self.context.route("**/*", self._request)
            await self.context.expose_binding("waypointManualEvent", self._manual)
            await self.context.add_init_script(
                """for(const kind of ['click','input'])document.addEventListener(kind,e=>{if(!e.isTrusted)return;const t=e.target.closest('button,a,input,select,textarea');if(t)window.waypointManualEvent({kind,tag:t.tagName,target:t.getAttribute('aria-label')||t.labels?.[0]?.innerText||(t.tagName==='INPUT'?'field':t.innerText||'control')})},true);"""
            )
            self.page = await self.context.new_page()
            self.context.on("page", self._popup)
            self.page.set_default_timeout(5000)
            await self.page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            await self.settle()
            return self
        except BaseException:
            if hasattr(self, "browser"):
                await self.browser.close()
            await self.pw.stop()
            raise

    async def __aexit__(self, *_):
        await self.browser.close()
        await self.pw.stop()

    async def _request(self, route):
        request = route.request
        if self.policy.request_allowed(
            request.url, request.method, request.resource_type
        ):
            await route.continue_()
        else:
            if (
                request.is_navigation_request()
                and request.frame == self.page.main_frame
            ):
                self.violation = "policy: navigation or method denied"
            self.event_sink(
                "request_blocked",
                resource_type=request.resource_type,
                method=request.method,
            )
            await route.abort()

    async def _popup(self, page):
        self.violation = "policy: unexpected popup; resume in original tab"
        await page.close()

    def _manual(self, source, event):
        if self.ownership.state == "human" and source["page"] == self.page:
            self.policy.check_url(source["frame"].url)
            if event.get("kind") in {"click", "input"}:
                self.event_sink("human_action", **sanitize_manual_event(event))

    async def _frames(self):
        if self.violation:
            raise ValueError(self.violation)
        self.policy.check_url(self.page.url)
        frames = [("", self.page.main_frame)]
        for frame in self.page.frames[1:]:
            try:
                self.policy.check_url(frame.url)
            except ValueError:
                continue
            element = await frame.frame_element()
            title = await element.get_attribute("title") or frame.name
            if title:
                frames.append((title, frame))
        return frames

    async def observe(self):
        all_frames = await self._frames()
        combined = Observation(title=await self.page.title())
        for name, frame in all_frames:
            data = await frame.evaluate(OBSERVE)
            combined.headings.extend(data["headings"])
            for k, v in data["fields"].items():
                combined.fields[k] = v if k not in combined.fields else "[ambiguous]"
            for control in data["controls"]:
                control["target"]["frame"] = name
                combined.controls.append(control)
            combined.tables.extend(data["tables"])
            combined.text += "\n" + data["text"]
            combined.structure += f"\nFRAME {name or 'main'}\n" + data["structure"]
            combined.dialog |= data["dialog"]
            combined.loading |= data["loading"]
        combined.frames = [name for name, _ in all_frames]
        return combined

    async def _scope(self, target):
        matches = [f for name, f in await self._frames() if name == target.frame]
        if len(matches) != 1:
            raise ValueError("ambiguous or unavailable frame")
        return matches[0]

    async def _locator(self, target: Target, inputs, *, root=None, unique=True):
        scope = root if root is not None else await self._scope(target)
        if target.row_input:
            value = str(inputs[target.row_input])
            scope = scope.get_by_role("row").filter(
                has=scope.get_by_role("cell", name=value, exact=True)
            )
        name = str(inputs[target.name_input]) if target.name_input else target.name
        if target.by == "css":
            locator = scope.locator(name)
        elif target.by == "role":
            locator = scope.get_by_role(target.role, name=name, exact=True)
        elif target.by == "label":
            locator = scope.get_by_label(name, exact=True)
        elif target.by == "title":
            locator = scope.get_by_title(name, exact=True)
        elif target.by == "placeholder":
            locator = scope.get_by_placeholder(name, exact=True)
        else:
            locator = scope.get_by_text(name, exact=True)
        if unique and await locator.count() != 1:
            raise ValueError("ambiguous or missing target")
        return locator

    async def resolve(self, target, inputs):
        locator = await self._locator(target, inputs)
        return {"unique": True, "visible": await locator.is_visible()}

    async def read(self, target, inputs, attribute="text"):
        locator = await self._locator(target, inputs)
        return await self._read_locator(locator, attribute)

    async def _read_locator(self, locator, attribute):
        if attribute == "text":
            return (await locator.inner_text()).strip()
        value = await locator.get_attribute(attribute)
        if value is None:
            raise ValueError("output attribute missing")
        return value

    async def read_rows(self, target, columns, inputs, limit):
        root = await self._locator(target, inputs, unique=False)
        count = await root.count()
        if count == 0:
            raise ValueError("output collection absent")
        rows = []
        for i in range(min(count, limit)):
            row = {}
            for col in columns:
                locator = (
                    await self._locator(col.target, inputs, root=root.nth(i))
                    if col.target
                    else root.nth(i)
                )
                row[col.name] = await self._read_locator(locator, col.attribute)
            rows.append(row)
        return rows

    async def settle(self, timeout_s=5):
        # Wait for a DOM quiet interval, capped by a deadline; navigation reloads
        # this detector. No fixed post-action sleep and no networkidle dependency.
        deadline = monotonic() + timeout_s
        while True:
            try:
                for _, frame in await self._frames():
                    await frame.evaluate(
                        """() => {if(!window.__waypointQuiet){window.__waypointQuiet={last:performance.now()};new MutationObserver(()=>window.__waypointQuiet.last=performance.now()).observe(document.documentElement,{childList:true,subtree:true,attributes:true,characterData:true})}else{window.__waypointQuiet.last=performance.now()}}"""
                    )
                    await frame.wait_for_function(
                        """() => {
                          if (!window.__waypointQuiet) {
                            window.__waypointQuiet={last:performance.now()};
                            new MutationObserver(()=>window.__waypointQuiet.last=performance.now()).observe(document.documentElement,{childList:true,subtree:true,attributes:true,characterData:true});
                            return false;
                          }
                          return document.readyState!=='loading' && performance.now()-window.__waypointQuiet.last>150 && ![...document.querySelectorAll('[aria-busy=true],[role=progressbar],[role=status]')].some(e=>e.getClientRects().length && (e.getAttribute('aria-busy')==='true'||e.getAttribute('role')==='progressbar'||/loading/i.test(e.innerText)));
                        }""",
                        timeout=max(1, (deadline - monotonic()) * 1000),
                    )
                return
            except BrowserError as exc:
                if (
                    monotonic() >= deadline
                    or "Execution context was destroyed" not in str(exc)
                ):
                    raise

    async def act(self, action, inputs):
        self.ownership.require_automation()
        obs = await self.observe()
        if obs.dialog:
            raise ValueError("blocking dialog requires intervention")
        started = monotonic()
        locator = await self._locator(action.target, inputs)
        facts = await locator.evaluate(
            """e=>({label:e.getAttribute('aria-label')||e.labels?.[0]?.innerText||(e.innerText||'').trim()||e.title||'',href:e.href||'',password:e.type==='password',file:e.type==='file',role:e.getAttribute('role')||'',expanded:e.getAttribute('aria-expanded'),form_method:e.form?.method,form_action:e.form?.action})"""
        )
        self.policy.check_action(action, facts)
        self.event_sink(
            "target_resolved",
            timing="target_resolution",
            duration_s=monotonic() - started,
            target=action.target.model_dump(),
        )
        self.ownership.require_automation()
        value = str(inputs[action.input]) if action.input else action.value
        started = monotonic()
        if action.kind == "fill":
            await locator.fill(value)
        elif action.kind == "select":
            await locator.select_option(label=value)
        elif action.kind == "click":
            await locator.click()
        elif action.kind == "press":
            await locator.press(value)
        elif action.kind == "check":
            await locator.check()
        else:
            raise ValueError("unsupported surface action")
        self.event_sink(
            "action_delivered", timing="action", duration_s=monotonic() - started
        )
        started = monotonic()
        await self.settle()
        self.event_sink(
            "wait", timing="application_wait", duration_s=monotonic() - started
        )

    async def capture(self, directory, name):
        from waypoint.evidence import sanitized

        files = []
        try:
            obs = await self.observe()
            snapshot = name + ".json"
            (directory / snapshot).write_text(json.dumps(sanitized(obs), indent=2))
            files.append(snapshot)
            screenshot = name + ".png"
            masks = [
                frame.locator("input,textarea,[contenteditable=true]")
                for _, frame in await self._frames()
            ]
            await self.page.screenshot(path=str(directory / screenshot), mask=masks)
            files.append(screenshot)
        except (BrowserError, ValueError):
            pass
        return files
