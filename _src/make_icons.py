"""Render the original app icon SVG to PNG sizes (192, 512, 180 apple-touch-icon).

Usage: python -X utf8 make_icons.py <pwa_dir>
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PWA = Path(sys.argv[1]).resolve()
svg = (PWA / "icon.svg").read_text(encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, size in (("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180)):
        pg = b.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
        pg.set_content(f'<html><body style="margin:0">{svg.replace("width=\"512\" height=\"512\"", f"width=\"{size}\" height=\"{size}\"")}</body></html>')
        pg.wait_for_timeout(150)
        pg.screenshot(path=str(PWA / name), clip={"x": 0, "y": 0, "width": size, "height": size})
        pg.close()
    b.close()
print("icons written to", PWA)
