"""Cross-check MKKomplete inputs against MK Warehouse (specials + fatalities).

Usage: python -I -X utf8 crosscheck.py <raw_dir> <src_dir>
"""
import html
import json
import re
import sys
from pathlib import Path

RAW, SRC = Path(sys.argv[1]), Path(sys.argv[2])
data = json.loads((SRC / "data.json").read_text(encoding="utf-8"))
mkw = json.loads((SRC / "mkw_special.json").read_text(encoding="utf-8"))
W = {"Forward": "F", "Back": "B", "Down": "D", "Up": "U", "1": "FP", "2": "BP", "3": "FK",
     "4": "BK", "Block": "BL", "Kameo": "KA", "Grab": "TH"}


def key_icem(s):
    s = re.sub(r"\([^()]*\)", lambda m: m.group(0) if "⟦" in m.group(0) and ":" not in m.group(0) else "", s)
    return [t for t in re.findall(r"⟦[db]:(\w+)⟧", s)]


def key_mkw(s):
    s = s.replace("Flip Stance", "FS")
    s = s.split(" or ")[0]
    out = []
    for w in re.findall(r"[A-Za-z0-9]+", s):
        if w in W:
            out.append(W[w])
        elif w == "FS":
            out.append("FS")
    return out


def norm(n):
    return re.sub(r"[^a-z]", "", n.lower())


ID = {c["id"]: c for c in data["chars"]}
alias = {"shao": "generalshao", "kenshi": "kenshitakahashi", "takeda": "takedatakahashi",
         "conan": "conanthebarbarian"}
report, ok, bad, miss = [], 0, 0, 0
for mid, rows in mkw.items():
    c = ID.get(alias.get(mid, mid))
    if not c:
        report.append(f"!! no char for {mid}")
        continue
    mine = {}
    for s in c["sections"]:
        if s["t"].startswith(("Special Moves", "Fatal Blow")):
            for it in s["items"]:
                if it.get("n"):
                    mine.setdefault(norm(it["n"].lstrip("*")), it["i"])
    for name, inp in rows:
        if not inp or inp.startswith("•") or name in ("Throws", "Special Moves", "Fatal Blow"):
            continue
        n = re.sub(r"^\(Air\)\s*|^Enhanced\s*|^(Close|Far)\s*", "", name)
        n = n.replace("Enhanced ", "")
        k = norm(n)
        if k not in mine:
            miss += 1
            continue
        a, b = key_icem(mine[k]), [x for x in key_mkw(inp) if x != "BL"]
        a = [x for x in a if x != "BL"]
        if a[:len(b)] == b or b[:len(a)] == a:
            ok += 1
        else:
            bad += 1
            report.append(f"{c['name']:<18} {name:<32} icem={' '.join(a):<22} mkw={' '.join(b)}")

# fatalities
fat = (RAW / "mk12_fatalities_.html").read_text(encoding="utf-8")
fat = fat[fat.find('id="characters"'):]
byname = {}
for c in data["chars"]:
    byname.setdefault((norm(c["name"]), c["group"] == "kameo"), c)
for short, full in [("shao", "generalshao"), ("kenshi", "kenshitakahashi"), ("takeda", "takedatakahashi"), ("conan", "conanthebarbarian")]:
    byname[(short, False)] = byname.get((full, False))
cur, kameo_part, fok, fbad = None, False, 0, 0
for m in re.finditer(r'<h4>([^<]*)</h4>|<h2 id="([^"]*)">.*?<a[^>]*>([^<]*)</a></h2>|<strong>([^<]*)</strong>\s*\((\w+)\)</div>\s*<div class="cmove12">([^<]*)</div>', fat, re.S):
    if m.group(1) is not None:
        kameo_part = "Kameo" in m.group(1)
        continue
    if m.group(2) is not None:
        kameo_part = m.group(2).endswith("kam")
        cur = byname.get((norm(html.unescape(m.group(3))), kameo_part))
        if not cur:
            report.append(f"!! fin char not found {m.group(3)} kameo={kameo_part}")
        continue
    if not cur:
        continue
    title, rng, inp = html.unescape(m.group(4)), m.group(5), key_mkw(html.unescape(m.group(6)))
    fin = []
    for s in cur["sections"]:
        if s["t"] in ("Finishers", "Fatality"):
            fin += [it for it in s["items"] if it.get("r") and not it.get("sub")]
    hit = [x for x in fin if key_icem(x["i"]) == inp]
    if hit:
        fok += 1
        if rng not in hit[0].get("r", ""):
            report.append(f"RNG {cur['name']:<16} {title:<40} mkw={rng} icem={hit[0].get('r')}")
    else:
        fbad += 1
        report.append(f"FIN {cur['name']:<16} {title:<40} mkw={' '.join(inp)} icem={[x['n']+': '+' '.join(key_icem(x['i'])) for x in fin]}")

print(f"specials ok={ok} mismatch={bad} not-matched-by-name={miss}; finishers ok={fok} mismatch={fbad}")
(SRC / "crosscheck_report.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
