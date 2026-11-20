"""Parse Altar of Gaming per-move properties (hit type, damage, frame data) into frames.json.

Usage: python -I -X utf8 parse_frames.py <aog_dir> <src_dir>
Keyed by fighter id -> list of {n, cat, i (PS token string), type, dmg, su, act, rec, hit, blk, pb, cxl}
"""
import html
import json
import re
import sys
from pathlib import Path

AOG, SRC = Path(sys.argv[1]), Path(sys.argv[2])
SLUG = {"christopher-peacemaker-smith": "peacemaker", "conan-the-barbarian": "conanthebarbarian",
        "john-homelander-gillman": "homelander", "kenshi": "kenshitakahashi", "takeda": "takedatakahashi",
        "shao-kahn": "generalshao"}
IMG = {"Square": "⟦b:FP⟧", "Triangle": "⟦b:BP⟧", "Cross": "⟦b:FK⟧", "Circle": "⟦b:BK⟧",
       "L1": "⟦b:TH⟧", "R1": "⟦b:KA⟧", "L2": "⟦b:FS⟧", "R2": "⟦b:BL⟧",
       "D Pad Left": "⟦d:B⟧", "D Pad Right": "⟦d:F⟧", "D Pad Down": "⟦d:D⟧", "D Pad Up": "⟦d:U⟧",
       "D Pad Top Right": "⟦d:UF⟧", "D Pad Top Left": "⟦d:UB⟧",
       "D Pad Bottom Right": "⟦d:DF⟧", "D Pad Bottom Left": "⟦d:DB⟧"}
FA = {"fa-comma": ", ", "fa-plus": " + ", "fa-chevrons-right": " » ", "fa-slash-forward": " / "}

FIELDS = {"Type": "type", "Damage": "dmg", "Block Damage": "bdmg", "Startup": "su", "Active": "act",
          "Recovery": "rec", "Hit Advantage": "hit", "Block Advantage": "blk",
          "Perfect Block Advantage": "pb", "Cancel Advantage": "cxl"}

out = {}
for f in sorted(AOG.glob("*.html")):
    cid = SLUG.get(f.stem, f.stem.replace("-", ""))
    src = f.read_text(encoding="utf-8", errors="replace")
    moves = []
    heads = list(re.finditer(r'<div\s+(?:id="toggle-move-\d+"\s+)?class="aog-section\s+(?:aog-section-toggle\s+)?aog-section-move\s+(move-category-\d+)([^"]*)"', src))
    for k, h in enumerate(heads):
        b = src[h.start():heads[k + 1].start() if k + 1 < len(heads) else len(src)]
        cat = h.group(1)
        nm = re.search(r'class="move-name">([^<]*)', b)
        if not nm:
            continue
        name = html.unescape(nm.group(1)).strip()
        m = re.search(r'<div\s+class="move-strings-container">(.*?)<div\s+class="move-types-container">', b, re.S)
        parts = []
        if m:
            for t in re.finditer(r'<img[^>]*>|fa-fw\s+(fa-[\w-]+)|<div\s+class="move-button-text"[^>]*>(.*?)</div>', m.group(1), re.S):
                tag = t.group(0)
                if tag.startswith("<img"):
                    if "action_key_playstation" in tag:
                        parts.append(IMG.get(re.search(r'title="([^"]*) \(PlayStation\)"', tag).group(1), "?"))
                elif t.group(1):
                    parts.append(FA.get(t.group(1), " "))
                else:
                    parts.append(" " + html.unescape(re.sub(r"<[^>]+>", "", t.group(2))).strip() + " ")
        rec = {"n": name, "cat": cat, "i": re.sub(r"\s+", " ", re.sub(r"⟧(?=⟦)", "⟧, ", "".join(parts))).strip()}
        for td in re.finditer(r"<td>([^<]+)</td>\s*<td[^>]*>([^<]*)</td>", b):
            key = FIELDS.get(td.group(1).strip())
            if key:
                rec[key] = td.group(2).strip()
        moves.append(rec)
    out[cid] = moves

(SRC / "frames.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "fighters,", sum(len(v) for v in out.values()), "moves,",
      sum(1 for v in out.values() for x in v if "su" in x), "with frame data")
