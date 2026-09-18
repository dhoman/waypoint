import json
from pathlib import Path

from waypoint.inspector import render_inspector
from waypoint.schema import Capability


def test_inspector_embeds_real_artifact_and_run_without_executable_ui_text(tmp_path):
    artifact = Capability.model_validate_json(open("evidence/capability.json").read())
    run = tmp_path / "run"
    run.mkdir()
    (run / "events.jsonl").write_text(
        json.dumps(
            {
                "event": "recognition",
                "state": "s2",
                "observation": {"text": "</script><script>alert(1)</script>"},
            }
        )
        + "\n"
    )
    (run / "result.json").write_text(
        json.dumps(
            {"status": "awaiting_intervention", "state": "s2", "transition": "t2"}
        )
    )
    output = tmp_path / "inspector.html"
    render_inspector(artifact, [run], output)
    rendered = output.read_text()
    assert "member-invoice-summary" in rendered
    assert "awaiting_intervention" in rendered
    assert "</script><script>alert(1)" not in rendered


async def test_inspector_selects_failed_transition_and_renders_rich_evidence(tmp_path):
    from playwright.async_api import async_playwright

    output = tmp_path / "inspector.html"
    artifact = Capability.model_validate_json(
        Path("evidence/capability-validated.json").read_text()
    )
    render_inspector(artifact, [Path("evidence/identity-mismatch")], output)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1500, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(output.as_uri())
        await page.locator(".edge.failed").click()
        assert await page.locator("#detail-title").inner_text() == "Transition t2"
        assert "identity" in await page.locator("#detail").inner_text()
        assert await page.locator("#evidence img").count() >= 1
        assert errors == []
        await page.screenshot(
            path=str(tmp_path / "inspector-preview.png"), full_page=True
        )
        await browser.close()
