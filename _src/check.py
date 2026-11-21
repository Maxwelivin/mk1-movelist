"""Render checks: console errors, every character page, mobile overflow, screenshots.

Usage: python -I -X utf8 check.py <html> <shot_dir>
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

page_path = Path(sys.argv[1]).resolve()
shots = Path(sys.argv[2])
shots.mkdir(parents=True, exist_ok=True)
url = page_path.as_uri()
errors = []

OVERFLOW_JS = """() => { const w = document.documentElement.clientWidth; const bad = [];
 for (const el of document.querySelectorAll('main *')) { const r = el.getBoundingClientRect();
   if (r.right > w + 1 && r.width > 0 && !el.closest('.jump')) bad.push(el.className + ':' + (el.textContent||'').slice(0,40)); }
 return [document.documentElement.scrollWidth - w, bad.slice(0,5)]; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for label, ctx_args in [("desktop", {"viewport": {"width": 1280, "height": 900}}),
                            ("mobile", {**p.devices["iPhone 13"]}),
                            ("small", {**p.devices["iPhone SE"]})]:
        ctx = b.new_context(**ctx_args)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(f"{label} pageerror {e}"))
        pg.on("console", lambda m: m.type == "error" and errors.append(f"{label} console {m.text}"))
        pg.goto(url)
        pages = pg.evaluate("DATA.chars.flatMap(c => c.tabs.map(t => 'c/' + c.id + '/' + t.id).concat(c.trial ? ['k/' + c.id] : []))")
        for view in pages:
            pg.evaluate(f"location.hash = '{view}'")
            pg.wait_for_timeout(25)
            n = pg.evaluate("document.querySelectorAll('.row').length")
            if n < 1:
                errors.append(f"{label} {view}: no rows")
            ov, bad = pg.evaluate(OVERFLOW_JS)
            if ov > 0 or bad:
                errors.append(f"{label} {view}: overflow {ov}px {bad}")
        for view in ["", "kameo", "controls", "c/scorpion", "c/tanya", "c/janetcage-kameo", "c/sektor"]:
            pg.evaluate(f"location.hash = '{view}'")
            pg.wait_for_timeout(80)
            ov, bad = pg.evaluate(OVERFLOW_JS)
            if ov > 0 or bad:
                errors.append(f"{label} view {view}: overflow {ov}px {bad}")
            if label != "small" or view in ("", "c/scorpion", "controls"):
                name = (view or "list").replace("/", "_")
                pg.screenshot(path=str(shots / f"{label}_{name}.png"), full_page=False)
        # search + mirror
        pg.evaluate("location.hash = ''")
        pg.fill("#q", "toasty")
        pg.wait_for_timeout(80)
        cnt = pg.evaluate("document.querySelectorAll('.row').length")
        if cnt < 1:
            errors.append(f"{label} search toasty found nothing")
        pg.screenshot(path=str(shots / f"{label}_search.png"))
        pg.fill("#q", "")
        ctx.close()
    b.close()

print("errors:", len(errors))
print("\n".join(errors[:60]))
