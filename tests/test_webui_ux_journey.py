"""UX Journey audits using the ux-audit tool for PoesIA webui.

Verifies end-to-end task completion and costs for:
1. Skipping Step 3 completely (Step 3 optional -> auto-draft full 14-line sonnet -> Step 4 -> listen).
2. Stanza thoughts per paragraph (optional inputs -> 1-click compose -> Step 4 -> listen).
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("ux_audit", reason="pip install -e ~/dev/ux-audit")
pytest.importorskip("playwright", reason="Browser tests require Playwright")

from ux_audit import Journey, Step, journey_failures, run_journey

URL = os.environ.get("POESIA_WEB_URL", "https://veriton.tail6b937e.ts.net:8443")


def setup_fresh(page):
    page.evaluate("() => sessionStorage.clear()")
    page.reload()
    page.wait_for_load_state("domcontentloaded")


def step_lang(page):
    page.wait_for_selector('#langStep button[data-lang="es"]')
    page.click('#langStep button[data-lang="es"]')
    page.wait_for_selector("#writer:not([hidden])")


def step_theme(page):
    page.wait_for_selector("#theme")
    page.fill("#theme", "El atardecer en el campo")
    page.fill("#reflection", "Un silencio de oro sobre las colinas.")
    page.click('#step1 button[data-goto="2"]')
    page.wait_for_selector("#step2:not([hidden])")


def step_form(page):
    page.wait_for_selector("#forms button.choice")
    page.click('#forms button.choice:has-text("Soneto")')
    page.click('#step2 button[data-goto="3"]')
    page.wait_for_selector("#step3:not([hidden])")


def step_skip_step3(page):
    page.wait_for_selector('#step3 button[data-goto="4"]')
    page.click('#step3 button[data-goto="4"]')
    page.wait_for_selector("#step4:not([hidden])", timeout=45000)
    page.wait_for_function(
        '() => document.getElementById("poemView").textContent.trim().split("\\n").filter(Boolean).length >= 14',
        timeout=45000,
    )


def step_stanza_thoughts_and_draft(page):
    page.wait_for_selector(".stanza-thought", timeout=10000)
    thoughts = page.query_selector_all(".stanza-thought")
    assert len(thoughts) == 4, f"Expected 4 stanza thought fields for sonnet, got {len(thoughts)}"
    thoughts[0].fill("La noche sobre el mar oscuro")
    thoughts[1].fill("El brillo del faro lejano")
    thoughts[2].fill("El susurro del viento marino")
    thoughts[3].fill("La calma de la orilla solitaria")

    page.click("#draftAllBtn")
    page.wait_for_function(
        '() => document.getElementById("in0").value.trim().length > 0', timeout=45000
    )
    page.wait_for_function(
        '() => document.getElementById("in13").value.trim().length > 0', timeout=45000
    )

    page.click('#step3 button[data-goto="4"]')
    page.wait_for_selector("#step4:not([hidden])", timeout=10000)
    page.wait_for_function(
        '() => document.getElementById("poemView").textContent.trim().split("\\n").filter(Boolean).length >= 14',
        timeout=10000,
    )


def step_listen(page):
    page.wait_for_selector("#listen")
    with page.expect_response(lambda r: "/api/readback" in r.url, timeout=45000) as resp_info:
        page.click("#listen")
    resp = resp_info.value
    assert resp.status == 200, f"Readback returned {resp.status}"
    ctype = resp.headers.get("content-type", "")
    assert "audio/" in ctype, f"Bad content type: {ctype}"


def test_ux_journey_skip_step_3() -> None:
    """Verifies that Step 3 is optional: advancing directly drafts the full poem."""
    journey = Journey(
        name="Spanish sonnet skipping Step 3",
        goal="skip step 3 completely, auto-draft full 14-verse sonnet, reach step 4, and recite via Piper TTS",
        setup=setup_fresh,
        steps=[
            Step("select Spanish language", step_lang),
            Step("enter theme and reflection", step_theme),
            Step("choose sonnet form", step_form),
            Step("skip step 3 directly to step 4", step_skip_step3),
            Step("listen to recited poem", step_listen),
        ],
        reached=lambda page: (
            page.is_visible("#step4")
            and len(
                [
                    ln
                    for ln in page.locator("#poemView").inner_text().strip().split("\n")
                    if ln.strip()
                ]
            )
            == 14
        ),
    )
    result = run_journey(journey, URL, ignore_https_errors=True)
    assert journey_failures(result) == [], f"Journey failed: {result.error}"
    assert result.reached
    assert result.cost == 5


def test_ux_journey_stanza_thoughts_and_draft() -> None:
    """Verifies optional thoughts per paragraph and 1-click composition."""
    journey = Journey(
        name="Spanish sonnet with stanza thoughts",
        goal="add thoughts per paragraph, 1-click compose full poem, reach step 4, and recite via Piper TTS",
        setup=setup_fresh,
        steps=[
            Step("select Spanish language", step_lang),
            Step("enter theme and reflection", step_theme),
            Step("choose sonnet form", step_form),
            Step("fill stanza thoughts and draft all", step_stanza_thoughts_and_draft, cost=5),
            Step("listen to recited poem", step_listen),
        ],
        reached=lambda page: (
            page.is_visible("#step4")
            and len(
                [
                    ln
                    for ln in page.locator("#poemView").inner_text().strip().split("\n")
                    if ln.strip()
                ]
            )
            == 14
        ),
    )
    result = run_journey(journey, URL, ignore_https_errors=True)
    assert journey_failures(result) == [], f"Journey failed: {result.error}"
    assert result.reached
    assert result.cost == 9
