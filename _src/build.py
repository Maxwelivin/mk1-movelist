"""Build the single-file MK1 PS5 move list page.

Usage: python -I -X utf8 build.py <src_dir> <out_html>
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
data = json.loads((SRC / "data.json").read_text(encoding="utf-8"))
zh = data["zh_finishers"]

MKW_ID = {"generalshao": "shao", "kenshitakahashi": "kenshi", "takedatakahashi": "takeda",
          "conanthebarbarian": "conan"}

# section title -> (kind, 中文標題, sort order)
KIND = [
    ("Special Moves", "special", "必殺技", 10),
    ("Fatal Blow", "fatalblow", "Fatal Blow", 20),
    ("Finishers", "finish", "終結技（Fatality／Animality）", 30),
    ("Fatality", "finish", "Kameo Fatality", 30),
    ("Basic Attacks", "basic", "普通技", 40),
    ("Black Dragon", "basic", "普通技", 41),
    ("Kombos", "kombo", "Kombo 招式串", 50),
    ("Basic Aerial Attacks", "air", "空中普通技", 60),
    ("Aerial Kombos", "airkombo", "空中 Kombo", 70),
    ("Throws", "throw", "投技", 80),
    ("Breakers", "breaker", "Breaker（連段破解）", 90),
    ("Taunts", "taunt", "挑釁", 95),
    ("Brutalities", "brutal", "Brutality", 100),
]

# disputed entries: (char id, item name, substring of input or "", message with tokens)
FLAGS = [
    ("sektor", "Fatality 2 - The Right Stuff", "", "MKWarehouse 寫作 ⟦d:B⟧, ⟦d:F⟧, ⟦d:B⟧, ⟦b:BP⟧（少一個方向）"),
    ("noobsaibot", "Dive Kick", "⟦d:B⟧, ⟦d:B⟧", "MKWarehouse 寫作 ⟦d:D⟧, ⟦d:B⟧, ⟦b:BK⟧（空中）"),
    ("noobsaibot", "Exorcism", "", "MKWarehouse 的強化版寫作 ⟦d:B⟧, ⟦d:D⟧, ⟦d:F⟧, ⟦b:FP⟧ + ⟦b:BL⟧"),
    ("tanya", "Deity Push", "⟦b:BK⟧", "MKWarehouse 寫作 Drill Kick 接：⟦d:B⟧, ⟦d:F⟧, 按住 ⟦b:BK⟧, 按住 ⟦d:B⟧（需 2 格 Guidance）"),
    ("tanya", "Umgadi Evade", "⟦b:BK⟧", "MKWarehouse 寫作 Drill Kick 接：⟦d:B⟧, ⟦d:F⟧, 按住 ⟦b:BK⟧, 按住 ⟦d:F⟧（需 2 格 Guidance）"),
    ("cyrax", "Fatality 1 - Burst Your Bubble", "", "距離：MKWarehouse 寫遠距離"),
    ("cyrax", "Fatality 2 - Bend It Like Bi-Han", "", "距離：MKWarehouse 寫遠距離"),
    ("noobsaibot", "Fatality 2 - Evil Chiropracty", "", "距離：MKWarehouse 寫近身"),
    ("reptile", "Fatality 2 - Acid Reflux", "", "距離：MKWarehouse 寫中距離"),
    ("khameleon-kameo", "", "", ""),  # placeholder resolved below
]


def kind_of(title):
    base, _, variant = title.partition(" - ")
    for key, kind, zt, order in KIND:
        if title.startswith(key) or base == key:
            if key == "Black Dragon":
                return kind, "普通技－" + title, order
            label = zt + ("－" + variant if variant else "")
            return kind, label, order
    return None


def finisher_key(name, is_kameo):
    if is_kameo:
        return "Kameo Fatality"
    m = re.match(r"^(Fatality \d|Animality)", name)
    return m.group(1) if m else None


chars = []
for c in data["chars"]:
    if c["group"] == "hidden":
        continue  # Floyd: AI-only secret fight, not playable
    is_kameo = c["group"] == "kameo"
    mkw_id = c["id"].replace("-kameo", "kam") if is_kameo else MKW_ID.get(c["id"], c["id"])
    zmap = zh.get(mkw_id, {})
    secs = []
    for s in c["sections"]:
        if s.get("dlc"):
            continue
        k = kind_of(s["t"])
        if not k:
            print("skip section", c["id"], s["t"])
            continue
        kind, label, order = k
        items = [dict(it) for it in s["items"] if not (it.get("n") == "N/A")]
        if kind == "finish" and not is_kameo:
            # split brutalities out of Finishers
            fin, bru, target = [], [], None
            for it in items:
                if not it.get("sub"):
                    target = bru if it.get("n", "").startswith("Brutality") else fin
                (target if target is not None else fin).append(it)
            items = fin
            if bru:
                secs.append({"k": "brutal", "t": "Brutality", "o": 100, "items": bru})
        if kind == "finish":
            for it in items:
                if it.get("sub"):
                    continue
                fk = finisher_key(it.get("n", ""), is_kameo)
                if fk and fk in zmap:
                    it["zh"] = zmap[fk]
        sec = {"k": kind, "t": label, "o": order, "items": items}
        if s.get("note"):
            sec["note"] = s["note"]
        secs.append(sec)
    secs.sort(key=lambda x: x["o"])
    for s in secs:
        s.pop("o")
    chars.append({"id": c["id"], "name": c["name"], "title": c["title"], "group": c["group"],
                  "pack": c["pack"], "secs": secs})

# Khameleon kameo fatality range dispute
FLAGS[-1] = ("khameleon-kameo", "", "", "距離：MKWarehouse 寫中距離")
byid = {c["id"]: c for c in chars}
applied = 0
for cid, name, sub, msg in FLAGS:
    c = byid[cid]
    hits = 0
    for s in c["secs"]:
        for it in s["items"]:
            nm = it.get("n", "")
            if cid == "khameleon-kameo":
                ok = s["k"] == "finish" and not it.get("sub")
            else:
                ok = (nm == name or (name in nm and "Dive Kick" in name)) and sub in it.get("i", "")
            if ok and nm:
                it["warn"] = msg
                hits += 1
    if not hits:
        raise SystemExit(f"flag not applied: {cid} {name}")
    applied += hits
print("flags applied:", applied)

meta = {"seasonal": data["seasonal"], "built": "2026-11-21",
        "src_icem": "2026-03-15"}
payload = json.dumps({"chars": chars, "meta": meta}, ensure_ascii=False, separators=(",", ":"))
tpl = (SRC / "template.html").read_text(encoding="utf-8")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")
rows = sum(len(s["items"]) for c in chars for s in c["secs"])
print(f"{len(chars)} chars, {rows} rows -> {OUT} ({OUT.stat().st_size // 1024} KB)")
