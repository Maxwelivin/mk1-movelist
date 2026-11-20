"""Parse Altar of Gaming "Challenge Kombos" (in-game Kombo Challenges) into trials.json,
and check that every special-move motion used in a trial exists in that fighter's move list.

Usage: python -I -X utf8 parse_trials.py <aog_dir> <src_dir>
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

data = json.loads((SRC / "data.json").read_text(encoding="utf-8"))
chars = {c["id"]: c for c in data["chars"]}


def tokens(s):
    return re.findall(r"⟦[db]:\w+⟧", s)


def motions(seq):
    """runs of >=2 directions immediately followed by an attack button."""
    out, run = [], []
    for t in seq:
        if t.startswith("⟦d:"):
            run.append(t)
        else:
            if len(run) >= 2 and t[3:5] in ("FP", "BP", "FK", "BK"):
                out.append(tuple(run + [t]))
            run = []
    return out


trials, report = {}, []
for f in sorted(AOG.glob("*.html")):
    slug = f.stem
    cid = SLUG.get(slug, slug.replace("-", ""))
    if cid not in chars:
        raise SystemExit(f"unknown character slug {slug}")
    src = f.read_text(encoding="utf-8", errors="replace")
    known = set()
    for s in chars[cid]["sections"]:
        if s["t"].startswith(("Special Moves", "Fatal Blow", "Basic Attacks", "Kombos")):
            for it in s["items"]:
                for m in motions(tokens(it.get("i", ""))):
                    known.add(m)
    items = []
    for b in re.split(r'<div\s+class="aog-section\s+aog-section-move\s+', src)[1:]:
        if not b.startswith("move-category-54"):
            continue
        name = html.unescape(re.search(r'class="move-name">([^<]*)', b).group(1)).strip()
        name = re.sub(r"^.*?Kombo\s*", "連段 ", name)
        body = re.search(r'<div\s+class="move-strings-container">(.*?)<div\s+class="move-types-container">', b, re.S).group(1)
        parts = []
        for m in re.finditer(r'<img[^>]*class="action_key_playstation[^"]*"[^>]*>|<img[^>]*>|<i[^>]*fa-fw\s+(fa-[\w-]+)[^>]*>|<div\s+class="move-button-text"[^>]*>(.*?)</div>', body, re.S):
            tag = m.group(0)
            if tag.startswith("<img"):
                if "action_key_playstation" not in tag:
                    continue
                t = re.search(r'title="([^"]*) \(PlayStation\)"', tag).group(1)
                if t not in IMG:
                    raise SystemExit(f"unknown button {t} in {slug}")
                parts.append(IMG[t])
            elif m.group(1):
                parts.append(FA[m.group(1)])
            else:
                parts.append(" " + html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip() + " ")
        s = "".join(parts)
        # join adjacent tokens with nothing between them (motion inputs) with ", "
        s = re.sub(r"⟧(?=⟦)", "⟧, ", s)
        s = re.sub(r"\s+", " ", s).strip()
        it = {"n": name, "i": s}
        # check per segment so a ↓ from the previous segment doesn't leak in
        bad = []
        for seg in s.split(" » "):
            for m in motions(tokens(seg)):
                if m not in known:
                    bad.append(m)
        if bad:
            it["chk"] = [" ".join(x) for x in bad]
            report.append(f"{cid:<18} {name:<8} {s}\n    not in move list: {it['chk']}")
        items.append(it)
    trials[cid] = items

(SRC / "trials.json").write_text(json.dumps(trials, ensure_ascii=False, indent=1), encoding="utf-8")
(SRC / "trials_report.txt").write_text("\n".join(report), encoding="utf-8")
total = sum(len(v) for v in trials.values())
print(f"{len(trials)} fighters, {total} trials, {len(report)} with unmatched special motions")
