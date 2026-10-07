import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

svg, png = Path(sys.argv[1]).resolve(), sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(
        viewport={
            "width": int(sys.argv[3]) if len(sys.argv) > 3 else 940,
            "height": int(sys.argv[4]) if len(sys.argv) > 4 else 690,
        }
    )
    page.goto(svg.as_uri())
    page.screenshot(path=png)
    b.close()
print("wrote", png)
