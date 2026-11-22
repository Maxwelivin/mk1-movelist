"""Build the private image pack (.mk1img) from downloaded official renders/mugshots.

The pack is for the owner's phone only: never commit it or the source images to the public repo.
Usage: python -I -X utf8 make_imgpack.py <img_dir> <out_file>
"""
import base64
import io
import json
import sys
from pathlib import Path
from PIL import Image

IMG, OUT = Path(sys.argv[1]), Path(sys.argv[2])


def webp(im, quality):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


images = {}
for f in sorted(IMG.glob("renders__*.png")):
    cid = f.stem.split("__", 1)[1]
    r = Image.open(f).convert("RGBA")
    box = r.getchannel("A").getbbox()
    if box:
        r = r.crop(box)
    r.thumbnail((600, 600), Image.LANCZOS)
    m = Image.open(IMG / f"mugshots__{cid}.png").convert("RGBA")
    m.thumbnail((120, 120), Image.LANCZOS)
    images[cid] = {"r": webp(r, 80), "m": webp(m, 82)}

pack = {"format": "mk1-imgpack", "version": 1, "created": "2026-11-22", "count": len(images), "images": images}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(pack, separators=(",", ":")), encoding="utf-8")
print(f"{len(images)} characters -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
