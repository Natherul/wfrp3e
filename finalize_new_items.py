import glob
import os
import json
import re
from collections import defaultdict
import random
import string

def generate_id(): return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

items_dir = "packs/source/items"

print("1. Fixing non-action layouts...")
updated_non_actions = 0
for f in glob.glob(os.path.join(items_dir, "*.json")):
    if "folders_" in f: continue
    with open(f, "r") as fp:
        try: data = json.load(fp)
        except: continue
        
    if data.get("type") != "action" and "system" in data and "conservative" in data["system"]:
        sys = data["system"]
        desc_parts = []
        if "requirements" in sys["conservative"]:
            desc_parts.append(sys["conservative"]["requirements"])
        if "effects" in sys["conservative"]:
            for eff_type, arr in sys["conservative"]["effects"].items():
                for eff in arr:
                    if "description" in eff:
                        text = eff["description"].replace("<p>", "").replace("</p>", "").strip()
                        if text: desc_parts.append(text)
        full_desc = " ".join(desc_parts)
        if not full_desc.startswith("<p>"): full_desc = f"<p>{full_desc}</p>"
        new_sys = {"description": full_desc}
        if data["type"] == "talent":
            new_sys["rechargeTokens"] = 0
            new_sys["socket"] = None
        if data["type"] == "criticalWound":
            sr = 1
            m = re.search(r'\b(\d+)\s*$', data.get("name", ""))
            if m: sr = int(m.group(1))
            new_sys["severityRating"] = sr
        data["system"] = new_sys
        with open(f, "w") as fp: json.dump(data, fp, indent=2, ensure_ascii=False)
        updated_non_actions += 1
print(f"   Fixed {updated_non_actions} non-action layouts.")

print("2. Removing empty generated back-face cards...")
deleted_empty = 0
for f in glob.glob(os.path.join(items_dir, "*.json")):
    if "folders_" in f: continue
    with open(f, "r") as fp:
        try: data = json.load(fp)
        except: continue
    if "_key" not in data:
        is_empty = False
        if data.get("type") == "action":
            sys = data.get("system", {})
            def check_face(fd):
                if not fd: return True
                reqs = fd.get("requirements", "").replace("<p>", "").replace("</p>", "").strip()
                if reqs: return False
                for k, v in fd.get("effects", {}).items():
                    if len(v) > 0:
                        for eff in v:
                            desc = eff.get("description", "").replace("<p>", "").replace("</p>", "").strip()
                            if desc: return False
                return True
            if check_face(sys.get("conservative")) and check_face(sys.get("reckless")):
                is_empty = True
        else:
            desc = data.get("system", {}).get("description", "").replace("<p>", "").replace("</p>", "").strip()
            if len(desc) < 5: is_empty = True
        if is_empty:
            os.remove(f)
            deleted_empty += 1
print(f"   Deleted {deleted_empty} empty items.")

print("3. Removing duplicates of pristine items...")
def fuzz_name(name):
    n = re.sub(r'\(?sr:?\s*\d+\)?', '', name, flags=re.IGNORECASE)
    n = re.sub(r'\d+', '', n)
    n = re.sub(r'[^a-zA-Z]', '', n).lower()
    return re.sub(r'[abcv]+$', '', n)

name_map = defaultdict(list)
for f in glob.glob(os.path.join(items_dir, "*.json")):
    if "folders_" in f: continue
    with open(f, "r") as fp:
        try: data = json.load(fp)
        except: continue
    if "name" in data:
        norm = fuzz_name(data["name"])
        if norm: name_map[norm].append({"path": f, "has_key": "_key" in data})

deleted_dupes = 0
for norm, items_list in name_map.items():
    if len(items_list) > 1:
        pristine = sum(1 for x in items_list if x["has_key"])
        gen = sum(1 for x in items_list if not x["has_key"])
        if pristine > 0 and gen > 0:
            for i in items_list:
                if not i["has_key"]:
                    os.remove(i["path"])
                    deleted_dupes += 1
        elif gen > 1 and pristine == 0:
            for i in range(1, len(items_list)):
                os.remove(items_list[i]["path"])
                deleted_dupes += 1
print(f"   Deleted {deleted_dupes} duplicate items.")

print("4. Mapping new items to correct folders...")
broad_folders = {
    "Actions": "ivXOnATwCKlIm1Tl", "Talents": "jF94s0lqlXKIEOms", "Wounds": "VUMz1tBRkXXXUVEt",
    "Mutations": generate_id(), "Insanities": generate_id(), "Diseases": generate_id(),
    "Conditions": generate_id(), "Trappings": generate_id(), "Abilities": generate_id()
}
for name, fid in broad_folders.items():
    fpath = os.path.join(items_dir, f"folders_{fid}.json")
    if not os.path.exists(fpath):
        with open(fpath, "w") as fp:
            json.dump({"name": name, "type": "Item", "_id": fid, "folder": None, "sorting": "a", "sort": 0, "color": None, "flags": {}, "_stats": {"systemId": "wfrp3e", "systemVersion": "1.0.0", "coreVersion": "11.315"}}, fp, indent=2)

mapped = 0
for f in glob.glob(os.path.join(items_dir, "*.json")):
    if "folders_" in f: continue
    with open(f, "r") as fp:
        try: data = json.load(fp)
        except: continue
    if "_key" not in data:
        t = data.get("type")
        if t == "action": data["folder"] = broad_folders["Actions"]
        elif t == "talent": data["folder"] = broad_folders["Talents"]
        elif t == "criticalWound": data["folder"] = broad_folders["Wounds"]
        elif t == "insanity": data["folder"] = broad_folders["Insanities"]
        elif t == "mutation": data["folder"] = broad_folders["Mutations"]
        elif t == "disease": data["folder"] = broad_folders["Diseases"]
        elif t == "condition": data["folder"] = broad_folders["Conditions"]
        elif t == "trapping": data["folder"] = broad_folders["Trappings"]
        else: data["folder"] = broad_folders["Abilities"]
        with open(f, "w") as fp: json.dump(data, fp, indent=2, ensure_ascii=False)
        mapped += 1
print(f"   Mapped {mapped} new items to logical folders.")

print("All new item finalizations complete! You can now run fix_all_text_qwen.py and then compile.")
