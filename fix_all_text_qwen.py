import glob
import os
import json
import requests
import time
import sys

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b"
items_dir = "packs/source/items"

def ask_qwen(payload_json):
    prompt = f"""You are an expert editor for Warhammer Fantasy Roleplay 3rd Edition.
Fix the spelling, missing spaces, and dice formatting in the following JSON values.
Replace OCR errors of dice (like [], [J, %%, W, etc) with proper tags:
{{Df}} = Fortune Die (White) - usually added by circumstances, boons, or items.
{{De}} = Expertise Die (Yellow) - usually added by being trained in a skill or having ranks.
{{Dc}} = Challenge Die (Purple) - usually added by difficult tasks.
{{Dm}} = Misfortune Die (Black) - usually added by negative circumstances, banes, or enemies.
{{Da}} = Action Die (Blue)
{{Dr}} = Reckless Die (Red)
{{Dco}} = Conservative Die (Green)

Also fix obvious OCR typos (e.g., 'Mele' -> 'Melee', 'aﬁected' -> 'affected', 'Asabove' -> 'As above', '[fyou' -> 'If you').
Do not change the keys of the JSON, only fix the text in the values.
Output ONLY a valid JSON object matching the input structure exactly.

Input JSON:
{json.dumps(payload_json, ensure_ascii=False)}
"""
    try:
        resp = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        }, timeout=120)
        res_text = resp.json().get("response", "")
        return json.loads(res_text)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def process_item(filepath):
    with open(filepath, "r") as fp:
        try: data = json.load(fp)
        except: return False
        
    if "_key" in data: return False # Skip pristine items
    if data.get("_text_fixed_by_llm"): return False # Skip already processed
    
    text_map = {}
    
    # Extract text from non-action descriptions
    sys_obj = data.get("system", {})
    if "description" in sys_obj and len(sys_obj["description"]) > 5:
        text_map["desc"] = sys_obj["description"]
        
    # Extract text from action sides
    for face in ["conservative", "reckless"]:
        if face in sys_obj:
            if "requirements" in sys_obj[face] and len(sys_obj[face]["requirements"]) > 5:
                text_map[f"{face}_req"] = sys_obj[face]["requirements"]
            if "effects" in sys_obj[face]:
                for etype, eff_list in sys_obj[face]["effects"].items():
                    for i, eff in enumerate(eff_list):
                        if "description" in eff and len(eff["description"]) > 2:
                            text_map[f"{face}_{etype}_{i}"] = eff["description"]
                            
    if not text_map:
        data["_text_fixed_by_llm"] = True
        with open(filepath, "w") as fp: json.dump(data, fp, indent=2, ensure_ascii=False)
        return True
        
    # Ask Qwen
    fixed_map = ask_qwen(text_map)
    if not fixed_map:
        return False
        
    # Apply fixes
    if "desc" in fixed_map:
        sys_obj["description"] = fixed_map["desc"]
        
    for face in ["conservative", "reckless"]:
        if face in sys_obj:
            req_key = f"{face}_req"
            if req_key in fixed_map:
                sys_obj[face]["requirements"] = fixed_map[req_key]
                
            if "effects" in sys_obj[face]:
                for etype, eff_list in sys_obj[face]["effects"].items():
                    for i, eff in enumerate(eff_list):
                        eff_key = f"{face}_{etype}_{i}"
                        if eff_key in fixed_map:
                            eff["description"] = fixed_map[eff_key]
                            
    data["_text_fixed_by_llm"] = True
    with open(filepath, "w") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
    return True


files = glob.glob(os.path.join(items_dir, "*.json"))
files = [f for f in files if "folders_" not in f]

# Count how many need processing
to_process = []
for f in files:
    with open(f, "r") as fp:
        try: d = json.load(fp)
        except: continue
    if "_key" not in d and not d.get("_text_fixed_by_llm"):
        to_process.append(f)

print(f"Found {len(to_process)} generated items needing LLM text fixes.")

for i, f in enumerate(to_process):
    if i % 10 == 0:
        print(f"[{i}/{len(to_process)}] Processing {os.path.basename(f)}...")
    success = False
    retries = 3
    while not success and retries > 0:
        success = process_item(f)
        retries -= 1
        if not success: time.sleep(2)
        
print("Completed all LLM text fixes!")
