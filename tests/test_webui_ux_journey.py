"""UX Journey audits using the ux-audit tool for PoesIA webui.

Verifies end-to-end task completion and costs for:
1. An empty Step 3 is not written for the person: "next" stays and says how to start
   (POSITIONING: the person is the author; a whole draft only when asked).
2. Stanza thoughts per paragraph (optional inputs -> draft all lines as a starting point ->
   lines shown as drafts until edited -> Step 4 -> listen).
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


def step_next_on_empty_step3(page):
    page.wait_for_selector('#step3 button[data-goto="4"]')
    page.click('#step3 button[data-goto="4"]')
    page.wait_for_function(
        '() => document.getElementById("draftStatus").textContent.trim().length > 0', timeout=5000
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
    assert page.evaluate(
        '() => [...document.querySelectorAll("textarea.verse")].every(t => t.classList.contains("drafted"))'
    ), "drafted lines must be marked as drafts until edited"

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


def test_ux_journey_empty_step_3_is_not_written_for_you() -> None:
    """ "Next" on an empty poem stays on Step 3 with a note; nothing is drafted unasked."""
    journey = Journey(
        name="Spanish sonnet, next on an empty Step 3",
        goal="press next with no lines: stay on step 3, see how to start, no line written",
        setup=setup_fresh,
        steps=[
            Step("select Spanish language", step_lang),
            Step("enter theme and reflection", step_theme),
            Step("choose sonnet form", step_form),
            Step("press next with no lines", step_next_on_empty_step3),
        ],
        reached=lambda page: (
            page.is_visible("#step3")
            and not page.is_visible("#step4")
            and page.input_value("#in0") == ""
        ),
    )
    result = run_journey(journey, URL, ignore_https_errors=True)
    assert journey_failures(result) == [], f"Journey failed: {result.error}"
    assert result.reached


def test_ux_journey_stanza_thoughts_and_draft() -> None:
    """Verifies optional thoughts per paragraph and 1-click composition."""
    journey = Journey(
        name="Spanish sonnet with stanza thoughts",
        goal="add thoughts per paragraph, draft all lines as a starting point, reach step 4, and recite",
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
