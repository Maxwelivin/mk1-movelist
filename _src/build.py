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
    ("Special Moves", "special", "SPECIAL MOVES", 10),
    ("Fatal Blow", "fatalblow", "FATAL BLOW", 20),
    ("Finishers", "finish", "FINISHERS", 30),
    ("Fatality", "finish", "KAMEO FATALITY", 30),
    ("Basic Attacks", "basic", "BASIC ATTACKS", 40),
    ("Black Dragon", "basic", "BASIC ATTACKS", 41),
    ("Kombos", "kombo", "KOMBOS", 50),
    ("Basic Aerial Attacks", "air", "AERIAL ATTACKS", 60),
    ("Aerial Kombos", "airkombo", "AERIAL KOMBOS", 70),
    ("Throws", "throw", "THROWS", 80),
    ("Breakers", "breaker", "BREAKERS", 90),
    ("Taunts", "taunt", "TAUNTS", 95),
    ("Brutalities", "brutal", "BRUTALITIES", 100),
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
                return kind, "BASIC ATTACKS · " + title.upper(), order
            label = zt + (" · " + variant.upper() if variant else "")
            return kind, label, order
    return None


def finisher_key(name, is_kameo):
    if is_kameo:
        return "Kameo Fatality"
    m = re.match(r"^(Fatality \d|Animality)", name)
    return m.group(1) if m else None


trials = json.loads((SRC / "trials.json").read_text(encoding="utf-8"))
TRIAL_NOTE = ("遊戲「Learn」教學中每位角色的 Kombo Challenge。» ＝前一招打中後馬上接下一段；"
              "⟦b:KA⟧ 是 Kameo 招式，請用遊戲教學指定的 Kameo 練。")
# trials whose directions are written as on-screen presses after a side switch (found by parse_trials.py)
TRIAL_FLAGS = [
    ("ashrah", "連段 6", "方向疑似左右相反：整組照「角色在右邊、面向左」的實際按法寫。照本站面向右的寫法，← → 要全部對調"
     "（例如 ⟦d:D⟧, ⟦d:F⟧, ⟦b:BP⟧ 應為 God's Wrath ⟦d:D⟧, ⟦d:B⟧, ⟦b:BP⟧）。請在遊戲中確認。"),
    ("sindel", "連段 6", "方向疑似左右相反：⟦d:F⟧ + ⟦b:KA⟧ 之後雙方換邊，後半段是換邊後的實際按法"
     "（⟦d:D⟧, ⟦d:F⟧, ⟦b:BP⟧ 應為 Levitate ⟦d:D⟧, ⟦d:B⟧, ⟦b:BP⟧）。請在遊戲中確認。"),
]
for cid, name, msg in TRIAL_FLAGS:
    hit = [t for t in trials[cid] if t["n"] == name and t.get("chk")]
    if len(hit) != 1:
        raise SystemExit(f"trial flag not matched: {cid} {name}")
    hit[0]["warn"] = msg
unflagged = [(k, t["n"]) for k, v in trials.items() for t in v if t.get("chk") and not t.get("warn")]
if unflagged:
    raise SystemExit(f"trials with unmatched motions but no flag: {unflagged}")

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
                secs.append({"k": "brutal", "t": "BRUTALITIES", "o": 100, "items": bru})
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
    if c["id"] in trials:
        secs.append({"k": "trial", "t": "KOMBO CHALLENGES", "o": 25, "note": TRIAL_NOTE,
                     "items": [{k: t[k] for k in ("n", "i", "warn") if k in t} for t in trials[c["id"]]]})
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

# ---- v3: per-move hit type / frame data / Easy Fatality from Altar of Gaming ----
frames = json.loads((SRC / "frames.json").read_text(encoding="utf-8"))
FD_KINDS = {"special", "fatalblow", "basic", "kombo", "air", "airkombo", "throw"}
SKIP_CATS = {"move-category-52", "move-category-53", "move-category-54"}  # finishers, brutalities, trials


def nkey(n):
    n = re.sub(r"^\((?:air|air close|close|far|mid)\)\s*", "", n.strip().lower())
    n = re.sub(r"(\s*\([^()]*\))+$", "", n)  # AoG stance suffixes: "(Sento Stance)", "(No Axe)"
    n = re.sub(r"[^a-z0-9]", "", n)
    return NAME_ALIAS.get(n, n)


# spelling differences between MKKomplete and AoG (General Shao)
NAME_ALIAS = {"superioritycomplex": "superioritykomplex", "superiorkomplex": "superioritykomplex",
              "harmstring": "hamstring"}


def stance_rank(sec_title, aog_name):
    """0 when the AoG stance suffix matches the section's stance variant, else 1."""
    tag = " ".join(re.findall(r"\(([^()]*)\)\s*$", aog_name)).lower()
    want = "sento" if "Sento" in sec_title else "no axe" if "Without Axe" in sec_title else ""
    return 0 if (want and want in tag) or (not want and ("sento" not in tag and "no axe" not in tag)) else 1


def toks(s, outer_only):
    if outer_only:  # drop parenthesised notes such as (Enhance: R2) but keep (D + FP)
        s = re.sub(r"\([^()]*\)", lambda m: m.group(0) if not re.search(
            r"[A-Za-z一-鿿]{2}", re.sub(r"⟦[db]:\w+⟧", "", m.group(0))) else "", s)
    out = []
    for t in re.findall(r"⟦[db]:(\w+)⟧", s):
        if t == "TH":  # throw button == FP + FK
            out += ["FP", "FK"]
        elif t != "BL":
            out.append(t)
    return out


EASY = {"fat": "Hold ⟦b:BL⟧, ⟦b:FK⟧", "ani": "Hold ⟦b:BL⟧, ⟦b:BP⟧", "kam": "Hold ⟦b:BL⟧, ⟦b:FP⟧"}
GAME_DMG = {("subzero", "Ice Slide"): "60.00", ("subzero", "Shove"): "20.00"}
# names as spelled in the in-game move list (MKKomplete spelling differs)
GAME_NAMES = {("subzero", "Ice Clone"): "Ice Klone", ("subzero", "Ice Clone Charge"): "Ice Klone Charge",
              ("madambo-kameo", "Bottle Toss - Close"): "Close Bottle Toss",
              ("madambo-kameo", "Bottle Toss - Far"): "Far Bottle Toss",
              ("madambo-kameo", "Enhanced Stumble Toward"): "Enhanced Sloshed Stumble Toward",
              ("madambo-kameo", "Enhanced Stumble Away"): "Enhanced Sloshed Stumble Away",
              ("madambo-kameo", "Drunken Dive"): "(Air) Drunken Dive",
              ("madambo-kameo", "The Customer is Wrong"): "The Customer Is Wrong"}
GAME_INPUT = {("subzero", "Ice Klone"): "⟦d:D⟧, ⟦d:B⟧, ⟦b:FP⟧ (Also in Air)（強化：出招後點一下 ⟦b:BL⟧）（完全強化：最後 ⟦b:FP⟧ + ⟦b:BL⟧ 同時按）"}
for c in chars:
    for s in c["secs"]:
        for it in s["items"]:
            new = GAME_NAMES.get((c["id"], it.get("n")))
            if new:
                it["n"] = new
            inp = GAME_INPUT.get((c["id"], it.get("n")))
            if inp:
                it["i"] = inp
renamed = sum(1 for c in chars for s in c["secs"] for it in s["items"] if (c["id"], it.get("n")) in {(k[0], v) for k, v in GAME_NAMES.items()})
if renamed != len(GAME_NAMES):
    raise SystemExit(f"GAME_NAMES applied {renamed}/{len(GAME_NAMES)}")

fd_hit = fd_badinput = 0
bad_log = []
for c in chars:
    if c["group"] != "main":
        continue
    recs = [r for r in frames.get(c["id"], []) if r["cat"] not in SKIP_CATS and "type" in r]
    by = {}
    for r in recs:
        if r["n"].lower().startswith("enhanced") or " enhanced " in r["n"].lower():
            continue
        by.setdefault(nkey(r["n"]), []).append(r)
    for s in c["secs"]:
        if s["k"] not in FD_KINDS:
            continue
        for it in s["items"]:
            if not it.get("n") or "fd" in it:
                continue
            cands = sorted(by.get(nkey(it["n"]), []), key=lambda r: stance_rank(s["t"], r["n"]))
            mine = toks(it.get("i", ""), True)
            pick = None
            for r in cands:
                theirs = toks(r["i"], False)
                if theirs and (mine[:len(theirs)] == theirs or theirs[:len(mine)] == mine):
                    pick = r
                    break
            if not pick:  # air moves: sources differ only in writing the jump direction (↗ / ↑) or not
                strip = lambda xs: [x for x in xs if x not in ("U", "UF")]
                for r in cands:
                    a, b = strip(mine), strip(toks(r["i"], False))
                    if a and (a == b):
                        pick = r
                        break
            if cands and not pick:
                fd_badinput += 1
                r = cands[0]
                bad_log.append(f"{c['id']:<16} {it['n']:<28} mine={' '.join(mine)}  aog={[' '.join(toks(r['i'], False)) for r in cands]}")
                note = "Altar of Gaming 寫作 " + r["i"]
                it["warn"] = (it["warn"] + "；另外 " + note) if it.get("warn") else note
            if pick:
                fd = {"t": pick["type"]}
                for k in ("su", "blk", "pb", "dmg"):
                    if pick.get(k):
                        fd[k] = pick[k]
                if pick.get("cxl") and s["k"] in ("basic", "kombo", "air", "airkombo"):
                    fd["cx"] = 1
                it["fd"] = fd
                fd_hit += 1
    # Easy versions: the in-game move list (Sub-Zero, photographed 2026-11-21) shows
    # Fatality = Hold R2, X ; Animality = Hold R2, Triangle ; Kameo Fatality = Hold R2, Square.
    fin = next((s for s in c["secs"] if s["k"] == "finish"), None)
    aog_ef = [r["i"] for r in frames.get(c["id"], []) if r["n"] == "Easy Fatality"]
    odd = [x for x in aog_ef if x not in (EASY["fat"], EASY["ani"], "⟦b:FK⟧ + ⟦b:BL⟧")]
    out, done = [], set()
    for it in fin["items"]:
        out.append(it)
        nm = it.get("n", "")
        kind = "fat" if nm.startswith("Fatality") else "ani" if nm.startswith("Animality") else None
        if kind and not it.get("sub"):
            last = kind == "ani" or not any(x.get("n", "").startswith("Fatality") for x in fin["items"][fin["items"].index(it) + 1:])
            if last and kind not in done:
                row = {"n": "Easy Fatality" if kind == "fat" else "Easy Animality", "i": EASY[kind], "sub": 1,
                       "zh": "簡易版（需 Easy Fatality 代幣）"}
                if odd:
                    row["warn"] = "!依遊戲內招式表的通用按法；Altar of Gaming 這位角色另寫有 " + "、".join(odd) + "，請在遊戲招式表確認。"
                out.append(row)
                done.add(kind)
    fin["items"] = out
for c in chars:  # Kameo Fatality easy version
    if c["group"] == "kameo":
        fin = next((s for s in c["secs"] if s["k"] == "finish"), None)
        if fin:
            fin["items"].append({"n": "Easy Fatality", "i": EASY["kam"], "sub": 1, "zh": "簡易版（需 Easy Fatality 代幣）"})
# damage checked against the in-game move list (Sub-Zero photos); AoG's Shove damage (130) is wrong
for c in chars:
    for s in c["secs"]:
        for it in s["items"]:
            fd = it.get("fd")
            if not fd:
                continue
            fix = GAME_DMG.get((c["id"], it.get("n")))
            if fix:
                fd["dmg"], it["warn"] = fix, "!傷害已依遊戲內招式表更正（Altar of Gaming 是舊數值）；幀數仍來自 Altar of Gaming，可能也是舊版本。"
            elif it.get("n") == "Shove":
                fd.pop("dmg", None)
(SRC / "frames_match_report.txt").write_text("\n".join(bad_log), encoding="utf-8")
print(f"frame data attached: {fd_hit} rows; name matched but input differs (not attached): {fd_badinput}")

# ---- v4: step-by-step breakdown of every Kombo Challenge ----
KIND_LABEL = {"special": "必殺技", "fatalblow": "Fatal Blow", "basic": "普通技", "kombo": "招式串",
              "air": "跳躍攻擊", "airkombo": "空中招式串", "throw": "投技"}
AIR_KINDS = {"air", "airkombo"}


def seg_toks(s):
    return tuple(re.findall(r"⟦[db]:(\w+)⟧", s))


def move_index(c):
    idx = {}
    for s in c["secs"]:
        if s["k"] not in KIND_LABEL:
            continue
        for it in s["items"]:
            if not it.get("n") or not it.get("i"):
                continue
            body = re.sub(r"\([^()]*\)", lambda m: m.group(0) if not re.search(
                r"[A-Za-z一-鿿]{2}", re.sub(r"⟦[db]:\w+⟧", "", m.group(0))) else "", it["i"])
            alts = body.split(" / ")  # "TH / (FP + FK)" style alternatives
            m2 = re.search(r"⟦b:(\w+)⟧/⟦b:(\w+)⟧", body)  # "(UF + FK/BK)": either button
            if m2:
                alts = [body.replace(m2.group(0), f"⟦b:{m2.group(1)}⟧"), body.replace(m2.group(0), f"⟦b:{m2.group(2)}⟧")]
            alts += [a.replace("⟦b:TH⟧", "⟦b:FP⟧ + ⟦b:FK⟧") for a in alts if "⟦b:TH⟧" in a]  # throw-ender strings
            for alt in alts:
                t = seg_toks(alt)
                if t:
                    idx.setdefault(t, []).append((it["n"], s["k"], it.get("i", "")))
                    if t[0] in ("UF", "U"):  # air kombos are often written without the jump direction
                        idx.setdefault(t[1:], []).append((it["n"], s["k"], it.get("i", "")))
    return idx


def pick_move(idx, t, in_air):
    cands = idx.get(t, [])
    if not cands:
        return None
    def score(m):
        n, k, inp = m
        air = k in AIR_KINDS or "(Air)" in n or "Air" in inp or "空中" in inp
        return (0 if air == in_air else 1, ["special", "kombo", "basic", "air", "airkombo", "throw", "fatalblow"].index(k))
    return sorted(cands, key=score)[0]


steps_total = steps_named = 0
for c in chars:
    if c["group"] != "main":
        continue
    idx = move_index(c)
    trial = next((s for s in c["secs"] if s["k"] == "trial"), None)
    if not trial:
        continue
    for it in trial["items"]:
        steps, prev_kind = [], None
        for k, seg in enumerate(it["i"].split(" » ")):
            seg = seg.strip()
            text = re.sub(r"⟦[db]:\w+⟧|[,+/]", " ", seg)
            in_air = "(Air)" in text or "While In Air" in text
            t = seg_toks(seg)
            st = {"i": seg}
            enhanced = "BL" in t and len(t) > 2
            core = tuple(x for x in t if x != "BL") if enhanced else t
            m = None
            if "KA" in t:
                st["k"], st["n"] = "Kameo", "叫 Kameo 出招"
            elif t == ("FS", "BL"):
                st["k"] = "Fatal Blow"
            elif t == ("F", "F"):
                st["k"], st["n"] = "移動", "前衝（快速按兩下 ⟦d:F⟧）"
            elif t == ("B", "B"):
                st["k"], st["n"] = "移動", "後撤（快速按兩下 ⟦d:B⟧）"
            elif len(t) == 2 and t[0] == "U" and t[1] in ("FP", "BP", "FK", "BK") and not in_air:
                st["k"], st["n"] = "跳躍攻擊", "原地往上跳，在空中按攻擊鍵"
            else:
                jump = bool(core) and core[0] in ("UF", "U", "UB")
                m = pick_move(idx, core, in_air) or pick_move(idx, t, in_air)
                if not m and jump and len(core) > 2:
                    m = pick_move(idx, core[1:], True)
                if m and jump and m[1] not in AIR_KINDS:  # a jump input can only be an air move
                    m = None
                if m:
                    st["n"] = re.sub(r"^\(Air\)\s*", "", m[0])
                    st["k"] = KIND_LABEL[m[1]]
                    if k > 0 and m[1] == "air" and prev_kind not in AIR_KINDS:
                        st["k"] = "空中追打"
            if enhanced and st.get("k") == "必殺技":
                st["k"] = "必殺技（強化版）"
            kind = m[1] if m else ("kameo" if st.get("k") == "Kameo" else None)
            # when to press it
            if in_air:
                hint = "自己還在空中（跳起來還沒落地）時輸入"
            elif k == 0:
                hint = ""
            elif prev_kind in AIR_KINDS and kind not in AIR_KINDS:
                hint = "落地後馬上按"
            elif kind in AIR_KINDS:
                hint = "前一招打中後跳起來，在空中出這段"
            elif kind == "special" and prev_kind in ("basic", "kombo"):
                hint = "前一招打到的瞬間就輸入（不用等動作做完）"
            elif kind == "kameo":
                hint = "前一段打中後叫出 Kameo"
            else:
                hint = "前一段打中後馬上接"
            if enhanced and kind == "special":
                hint = (hint + "；" if hint else "") + "最後加按 ⟦b:BL⟧，耗 1 格能量"
            if hint:
                st["h"] = hint
            steps.append(st)
            steps_total += 1
            steps_named += bool(st.get("n") or st.get("k"))
            prev_kind = kind
        it["steps"] = steps
print(f"trial steps: {steps_named}/{steps_total} identified")

# ---- v8: in-game move list layout (BASIC ATTACKS / SPECIAL MOVES / KAMEO MOVES / FINISHERS) ----


def variant(sec):
    return sec["t"].split(" · ", 1)[1] if " · " in sec["t"] else ""


def chain(basics, kombos):
    """Put each kombo string right under the basic attack it starts with (like the in-game list)."""
    bt = [toks(b.get("i", ""), True) for b in basics]
    attach, rest = {i: [] for i in range(len(basics))}, []
    for k in kombos:
        kt = toks(k.get("i", ""), True)
        best = None
        for i, t in enumerate(bt):
            if t and len(kt) > len(t) and kt[:len(t)] == t and (best is None or len(t) > len(bt[best])):
                best = i
        (attach[best] if best is not None else rest).append(k)
    out = []
    for i, b in enumerate(basics):
        out.append(b)
        out += [dict(k, ch=1) for k in attach[i]]
    return out + rest


chained = unchained = 0
for c in chars:
    secs = c.pop("secs")
    by = {}
    for s in secs:
        by.setdefault(s["k"], []).append(s)
    tabs = []
    if c["group"] == "main":
        groups, vs = [], []
        for s in by.get("basic", []) + by.get("kombo", []):
            if variant(s) not in vs:
                vs.append(variant(s))
        for v in vs:
            b = [it for s in by.get("basic", []) if variant(s) == v for it in s["items"]]
            k = [it for s in by.get("kombo", []) if variant(s) == v for it in s["items"]]
            items = chain(b, k)
            n_ch = sum(1 for it in items if it.get("ch"))
            chained += n_ch
            unchained += len(k) - n_ch
            groups.append({"h": v, "items": items})
        avs = []
        for s in by.get("air", []) + by.get("airkombo", []):
            if variant(s) not in avs:
                avs.append(variant(s))
        for v in avs:
            b = [it for s in by.get("air", []) if variant(s) == v for it in s["items"]]
            k = [it for s in by.get("airkombo", []) if variant(s) == v for it in s["items"]]
            groups.append({"h": "AERIAL ATTACKS" + (" · " + v if v else ""), "items": chain(b, k)})
        for kind, h in (("throw", "THROWS"), ("breaker", "BREAKERS"), ("taunt", "TAUNTS")):
            for s in by.get(kind, []):
                groups.append({"h": h, "items": s["items"]})
        tabs.append({"id": "basic", "t": "BASIC ATTACKS", "groups": groups})
        groups = [{"h": "SPECIAL MOVES" + (" · " + variant(s) if variant(s) else ""), "items": s["items"]} for s in by.get("special", [])]
        groups += [{"h": "FATAL BLOW", "items": s["items"]} for s in by.get("fatalblow", [])]
        tabs.append({"id": "special", "t": "SPECIAL MOVES", "groups": groups})
        tabs.append({"id": "kameo", "t": "KAMEO MOVES", "groups": []})  # filled in the browser from the chosen Kameo
        fat, ani, cur = [], [], None
        for s in by.get("finish", []):
            for it in s["items"]:
                if not it.get("sub"):
                    cur = ani if it.get("n", "").startswith("Animality") else fat
                (cur if cur is not None else fat).append(it)
        groups = [{"h": "FATALITIES", "items": fat}, {"h": "ANIMALITY", "items": ani}]
        groups += [{"h": "BRUTALITIES", "items": s["items"], "fold": 1} for s in by.get("brutal", [])]
        tabs.append({"id": "finish", "t": "FINISHERS", "groups": groups})
        if by.get("trial"):
            c["trial"] = by["trial"][0]["items"]
    else:
        groups = []
        for s in by.get("special", []):
            v = variant(s)
            h = "MAIN FIGHTER MOVES" if v == "MAIN CHARACTER" else "KAMEO MOVES" + (" · " + v if v and v != c["name"].upper() else "")
            groups.append({"h": h, "items": s["items"]})
        groups += [{"h": "THROWS", "items": s["items"]} for s in by.get("throw", [])]
        tabs.append({"id": "kameo", "t": "KAMEO MOVES", "groups": groups})
        groups = [{"h": "KAMEO FATALITY", "items": s["items"]} for s in by.get("finish", [])]
        groups += [{"h": "BRUTALITIES", "items": s["items"], "fold": 1} for s in by.get("brutal", [])]
        tabs.append({"id": "finish", "t": "FINISHERS", "groups": groups})
    left = set(by) - {"basic", "kombo", "air", "airkombo", "throw", "breaker", "taunt", "special",
                      "fatalblow", "finish", "brutal", "trial"}
    if left:
        raise SystemExit(f"{c['id']}: sections not placed in tabs: {left}")
    c["tabs"] = tabs
print(f"v8 tabs: kombo strings under a starter {chained}, left at end of group {unchained}")

meta = {"seasonal": data["seasonal"], "built": "2026-11-21",
        "src_icem": "2026-03-15", "version": "v9", "fd_count": fd_hit}
payload = json.dumps({"chars": chars, "meta": meta}, ensure_ascii=False, separators=(",", ":"))
tpl = (SRC / "template.html").read_text(encoding="utf-8")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")
# PWA files next to the page (icons are rendered by make_icons.py)
PWA = SRC / "pwa"
for f in ("manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png"):
    (OUT.parent / f).write_bytes((PWA / f).read_bytes())
(OUT.parent / "sw.js").write_text((PWA / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", meta["version"]), encoding="utf-8")
rows = sum(len(g["items"]) for c in chars for t in c["tabs"] for g in t["groups"]) + sum(len(c.get("trial", [])) for c in chars)
print(f"{len(chars)} chars, {rows} rows -> {OUT} ({OUT.stat().st_size // 1024} KB)")
