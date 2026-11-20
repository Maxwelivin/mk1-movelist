"""Parse MKKomplete (icemantraveler) + MK Warehouse pages into data.json.

Usage: python -I -X utf8 parse.py <raw_dir> <out_json>
"""
import html
import json
import re
import sys
from pathlib import Path

RAW = Path(sys.argv[1])
OUT = Path(sys.argv[2])

# combos page is PS5 notation; normalise to universal tokens
PS_TO_UNI = {"&#9634;": "FP", "&#916;": "BP", "&#10005;": "FK", "O": "BK",
             "L1": "TH", "R1": "KA", "L2": "FS", "R2": "BL"}
DIRS = {"F", "B", "D", "U", "UF", "UB", "DF", "DB"}
BTNS = {"FP", "BP", "FK", "BK", "TH", "KA", "FS", "BL"}
_R = r"(?:Close|Mid|Far|Very Far|Anywhere|Jump|Fullscreen)"
RANGE_RE = re.compile(r"\s*\((" + _R + r"(?:\s*[-/]\s*" + _R + r")*)\)\s*(?:\[([^\]]*)\])?\s*$", re.I)
DMG_RE = re.compile(r"\s*\[([\d.]+)\]\s*$")


def tokenize(fragment, ps):
    def dir_sub(m):
        d = m.group(1).strip()
        if d not in DIRS:
            raise ValueError(f"unknown dir {d!r}")
        return f"⟦d:{d}⟧"

    def sym_sub(m):
        b = m.group(1).strip()
        if ps:
            b = PS_TO_UNI.get(b, b)
        if b not in BTNS:
            raise ValueError(f"unknown button {b!r}")
        return f"⟦b:{b}⟧"

    s = re.sub(r'<b class="dir[^"]*">([^<]*)</b>', dir_sub, fragment)
    s = re.sub(r'<b class="sym[^"]*">([^<]*)</b>', sym_sub, s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    # tidy spacing around tokens: "( ⟦d:D⟧+⟦b:BP⟧ )" -> "(⟦d:D⟧ + ⟦b:BP⟧)"
    s = re.sub(r"\s*\+\s*", " + ", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    s = re.sub(r"\s*,\s*", ", ", s)
    return s


def parse_line(raw, ps):
    sub = raw.lstrip().startswith("&nbsp;")
    text = tokenize(raw, ps)
    if not text:
        return None
    item = {"n": "", "i": ""}
    m = re.match(r"^([^⟦:]+?):\s*(.*)$", text)
    if m:
        item["n"], rest = m.group(1).strip(), m.group(2).strip()
        if not rest:
            return {"h": item["n"]}  # sub-header such as "Heaven Mode:"
    else:
        rest = text
        if not sub and "⟦" not in text:
            item["n"], rest = text, ""
    mm = DMG_RE.search(rest)
    if mm:
        item["dmg"] = mm.group(1)
        rest = rest[:mm.start()]
    mm = RANGE_RE.search(rest)
    if mm:
        item["r"] = re.sub(r"\s*([-/])\s*", r"", mm.group(1))
        if mm.group(2):
            item["rn"] = mm.group(2)
        rest = rest[:mm.start()]
    item["i"] = rest.strip()
    if sub:
        item["sub"] = 1
    return item


def parse_block(block, ps):
    sections = []
    for p in re.finditer(r'<p class="(\w+)">(.*?)</p>', block, re.S):
        cls, body = p.group(1), p.group(2)
        if cls in ("bio", "howtofight"):
            continue
        hm = re.match(r"\s*<u><b>([^<]*)</b></u>(.*)", body, re.S)
        if not hm:
            continue
        title = hm.group(1).strip().rstrip(":")
        body = hm.group(2).replace("\n", " ")
        lines = re.split(r"<br\s*/?>", body)
        intro = tokenize(lines[0], ps)
        items = []
        for ln in lines[1:]:
            it = parse_line(ln, ps)
            if it and not (it.get("n") == "N/A" and not it.get("i")):
                items.append(it)
        sec = {"t": title, "items": items}
        if intro:
            sec["note"] = intro.lstrip("*").strip()
        if cls == "dlc":
            sec["dlc"] = 1
        sections.append(sec)
    return sections


def split_chars(src, ps):
    anchors = list(re.finditer(r'<a href="#top" name="([^"]+)">.*?<b>([^<]+)</b>([^<]*)', src))
    out = {}
    for k, a in enumerate(anchors):
        end = anchors[k + 1].start() if k + 1 < len(anchors) else len(src)
        block = src[a.start():end]
        cut = block.find("Seasonal_Fatalities")
        if cut > 0:
            block = block[:cut]
        out[a.group(1)] = {"name": a.group(2).strip(),
                           "title": a.group(3).strip(),
                           "sections": parse_block(block, ps)}
    return out


main_src = (RAW / "icem.html").read_text(encoding="utf-8", errors="replace")
combo_src = (RAW / "icem_combos.html").read_text(encoding="utf-8", errors="replace")
main = split_chars(main_src, ps=False)
combos = split_chars(combo_src, ps=True)

# seasonal fatalities (universal)
sm = re.search(r'name="Seasonal_Fatalities".*?<hr class="main">(.*?)<a href="#top">', main_src, re.S)
seasonal = [parse_line(x, False) for x in re.split(r"<br\s*/?>", sm.group(1))]
seasonal = [x for x in seasonal if x]


def slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


chars = []
for key, d in main.items():
    if key in ("top",):
        continue
    if key.startswith("Kameo_"):
        group = "kameo"
    elif key == "Floyd":
        group = "hidden"
    else:
        group = "main"
    title = d["title"]
    pack = "base"
    if "KP1" in title or key in ("Shang Tsung", "Omni-Man", "Quan Chi", "Peacemaker", "Ermac", "Homelander", "Takeda"):
        pack = "kp1"
    if key.startswith("KP2_") or "KP2" in title:
        pack = "kp2"
    if group == "kameo":
        idx = list(main).index(key)
        kp1_start = list(main).index("Kameo_Tremor")
        pack = "kp2" if key == "Kameo_Madam_Bo" else ("kp1" if idx >= kp1_start else "base")
    title = re.sub(r"\[.*?\]", "", title).strip().strip("()").strip()
    secs = d["sections"]
    combo_key = key
    if combo_key in combos:
        secs = combos[combo_key]["sections"] + secs
    chars.append({"id": slug(d["name"]) + ("-kameo" if group == "kameo" else ""),
                  "name": d["name"], "title": title, "group": group, "pack": pack,
                  "sections": secs})

# ---- MK Warehouse cross-check data --------------------------------------
WORD = {"Forward": "F", "Back": "B", "Down": "D", "Up": "U", "1": "FP", "2": "BP",
        "3": "FK", "4": "BK", "Block": "BL", "Kameo": "KA", "Grab": "TH",
        "Flip": "FS", "Stance": ""}


def mkw_rows(fname):
    s = (RAW / fname).read_text(encoding="utf-8")
    res, cur = {}, None
    for m in re.finditer(r'<h2 id="([^"]+)">|<div class="row"><div class="cname">(.*?)</div>(?:<div class="cmove12">(.*?)</div>)?</div>', s):
        if m.group(1):
            cur = m.group(1)
            res[cur] = []
        elif cur:
            res[cur].append((html.unescape(re.sub(r"<[^>]+>", "", m.group(2) or "")),
                             html.unescape(m.group(3) or "")))
    return res


mkw = mkw_rows("special_gen.html")

# Traditional Chinese finisher names from MKW (fatalities/chinese-hk), keyed by MKW anchor id
hk = (RAW / "fat_hk.html").read_text(encoding="utf-8")
zh, cur = {}, None
for m in re.finditer(r'<h2 id="([^"]+)"|<strong>([^<:]+):\s*（[^）]*）([^<]+)</strong>', hk):
    if m.group(1):
        cur = m.group(1)
        zh[cur] = {}
    elif cur:
        zh[cur][m.group(2).strip()] = m.group(3).strip()

data = {"chars": chars, "seasonal": seasonal, "zh_finishers": zh,
        "mkw_names": sorted(mkw)}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT.parent / "mkw_special.json").write_text(json.dumps(mkw, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(chars), "characters;", sum(len(it["items"]) for c in chars for it in c["sections"]), "rows")
