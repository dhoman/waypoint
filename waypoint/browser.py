"""The only module that knows Playwright objects; one async session owner."""

from playwright.async_api import async_playwright

from waypoint.schema import Action, Inputs, Observation, Target

# Controlled observation implementation, never model/artifact-provided script.
OBSERVE = """() => {
 const visible=e=>!!(e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden';
 const text=e=>(e.innerText||'').trim();
 const fields={};document.querySelectorAll('dt').forEach(e=>{fields[text(e)]=text(e.nextElementSibling)});
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

    def __init__(self, url: str, *, headed=False):
        self.url = url
        self.headed = headed

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=not self.headed)
        self._context = await self._browser.new_context(
            viewport={"width": 1200, "height": 850}
        )
        self._page = await self._context.new_page()
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

    async def _frame(self):
        iframe = self._page.locator('iframe[title="Member workspace"]')
        if await iframe.count() != 1:
            raise ValueError("ambiguous or missing application frame")
        return await (await iframe.element_handle()).content_frame()

    async def observe(self) -> Observation:
        return Observation.model_validate(await (await self._frame()).evaluate(OBSERVE))

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
        locator = await self._resolve(action.target, inputs)
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
