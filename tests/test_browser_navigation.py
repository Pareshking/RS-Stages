"""Real-browser regression test for the production navigation path.

AppTest exercises Streamlit's Python event model, but it cannot catch a browser-side
blank page. This test launches the actual Streamlit server and clicks the same
segmented-control buttons a user clicks in the deployed app.
"""

import os

from playwright.sync_api import Page, expect


VIEWS = {
    "Dashboard": "Today’s briefing",
    "Screener": "Screener",
    "Industries": "Industry strength",
    "Market": "Market regime",
    "Movers": "What changed",
    "Stock": "Symbol",
    "Methodology": "Methodology",
}


def test_production_navigation_in_real_browser(page: Page):
    base_url = os.environ.get("RS_STAGES_TEST_URL", "http://127.0.0.1:8501")
    page.goto(base_url, wait_until="networkidle", timeout=60_000)

    nav = page.locator('[data-testid="stSegmentedControl"]')
    expect(nav).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Today’s briefing", exact=True)).to_be_visible(timeout=30_000)

    for view, marker in VIEWS.items():
        if view == "Dashboard":
            continue
        nav.get_by_role("button", name=view, exact=True).click()
        expect(page.get_by_text(marker, exact=True)).to_be_visible(timeout=30_000)
        # The app must have produced a non-empty Streamlit main area after the rerun.
        expect(page.locator('[data-testid="stMain"]')).not_to_be_empty(timeout=30_000)

    nav.get_by_role("button", name="Dashboard", exact=True).click()
    expect(page.get_by_text("Today’s briefing", exact=True)).to_be_visible(timeout=30_000)
