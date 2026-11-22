"""End-to-end test of v9 over HTTP: service worker, image pack import, persistence, offline, own image.

Usage: python -X utf8 test_v9.py <dist_dir> <pack_file> <shot_dir>
"""
import http.server
import socketserver
import sys
import threading
from functools import partial
from pathlib import Path
from playwright.sync_api import sync_playwright

DIST, PACK, SHOTS = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
SHOTS.mkdir(exist_ok=True)
handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/"
results = []


def ok(name, cond, extra=""):
    results.append(("PASS" if cond else "FAIL") + f"  {name} {extra}")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(**p.devices["iPhone 13"])
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_timeout(1500)
    ok("service worker registered", pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !!r)"))
    ok("manifest linked", pg.evaluate("!!document.querySelector('link[rel=manifest]')"))
    ok("no images before import", pg.evaluate("imgCount()") == 0)
    pg.goto(url + "#images")
    pg.wait_for_timeout(400)
    pg.set_input_files("#impf", str(PACK))
    pg.wait_for_function("document.querySelector('#imgmsg') && /匯入完成|匯入失敗/.test(document.querySelector('#imgmsg').textContent)", timeout=30000)
    msg = pg.inner_text("#imgmsg")
    ok("import message", "匯入完成" in msg, msg)
    pg.wait_for_timeout(1200)
    n = pg.evaluate("imgCount()")
    ok("all characters have images", n == 56, f"({n})")
    pg.screenshot(path=str(SHOTS / "v9_images_page.png"))
    pg.goto(url + "#")
    pg.wait_for_timeout(600)
    ok("list thumbnails", pg.evaluate("document.querySelectorAll('.alist img.th').length") == 35)
    pg.evaluate("scrollTo(0, 1250)")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(SHOTS / "v9_list.png"))
    pg.goto(url + "#c/subzero")
    pg.wait_for_timeout(600)
    ok("character render shown", pg.evaluate("!!document.querySelector('.cimg img') && document.querySelector('.cimg img').naturalWidth > 100"))
    pg.evaluate("scrollTo(0, 330)")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(SHOTS / "v9_char.png"))
    pg.goto(url + "#c/subzero/kameo")
    pg.wait_for_timeout(500)
    ok("kameo thumbnail", pg.evaluate("!!document.querySelector('.kth')"))
    # persistence across reload
    pg.reload()
    pg.wait_for_timeout(1200)
    ok("images persist after reload", pg.evaluate("imgCount()") == 56)
    # offline: page + data come from the service worker cache
    ctx.set_offline(True)
    pg.reload()
    pg.wait_for_timeout(1500)
    ok("works offline", pg.evaluate("typeof DATA === 'object' && DATA.chars.length") == 56)
    ok("images offline", pg.evaluate("imgCount()") == 56)
    ctx.set_offline(False)
    # own image for one character
    pg.goto(url + "#c/scorpion")
    pg.wait_for_timeout(500)
    pg.set_input_files("input[data-ownimg=scorpion]", str(DIST / "icon-512.png"))
    pg.wait_for_timeout(1500)
    src = pg.evaluate("document.querySelector('.cimg img') ? document.querySelector('.cimg img').src.slice(0, 22) : ''")
    ok("own image replaces render", src.startswith("data:image/"), src)
    ok("no page errors", not errs, "; ".join(errs[:3]))
    b.close()
srv.shutdown()
print("\n".join(results))
