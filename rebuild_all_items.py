import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import glob
import os
import json
import random
import string
import re

def generate_id(): return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def clean_name(filename):
    name = os.path.splitext(filename)[0]
    name = name.replace('_', ' ')
    base_name = re.sub(r' [AC]$', '', name).strip()
    face = 'base'
    if name.endswith(' A'): face = 'reckless'
    elif name.endswith(' C'): face = 'conservative'
    return base_name, face

def get_base_folder(path):
    lower = path.lower()
    if 'talent' in lower: return 'Talents'
    if 'action' in lower: return 'Actions'
    if 'insanity' in lower: return 'Insanities'
    if 'wound' in lower: return 'Wounds'
    if 'mutation' in lower or 'chaos mark' in lower: return 'Mutations'
    if 'miscast' in lower: return 'Miscasts'
    if 'disease' in lower: return 'Diseases'
    if 'condition' in lower: return 'Conditions'
    if 'object' in lower or 'trapping' in lower: return 'Trappings'
    return 'Abilities'

def cluster_points(pts, dist=15):
    clusters = []
    for p in pts:
        found = False
        for c in clusters:
            if abs(p[0] - c[0][0]) < dist and abs(p[1] - c[0][1]) < dist:
                c.append(p)
                found = True
                break
        if not found: clusters.append([p])
    return [(int(sum(p[0] for p in c)/len(c)), int(sum(p[1] for p in c)/len(c))) for c in clusters]

def extract_symbols(img):
    symbols = {}
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
    
    def scan(name, thresh):
        tpl = cv2.imread(f"templates/template_{name}.png", 0)
        if tpl is None: return []
        res = cv2.matchTemplate(gray_img, tpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= thresh)
        return cluster_points(list(zip(*loc[::-1])))

    symbols['hammer'] = scan("hammer", 0.70)
    symbols['eagle'] = scan("eagle", 0.70)
    symbols['skull'] = scan("skull", 0.70)
    symbols['comet'] = scan("comet", 0.70)
    symbols['chaos'] = scan("chaos", 0.70)
    
    symbols['challenge'] = scan("challenge", 0.65)
    symbols['failure'] = scan("failure", 0.60)
    symbols['black'] = scan("black", 0.65)
    return symbols

def get_text_lines(img):
    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    lines = []
    for i in range(len(d['text'])):
        text = d['text'][i].strip()
        if len(text) == 0 or int(d['conf'][i]) < 40: continue
        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
        
        placed = False
        for line in lines:
            if abs(line['y'] - y) <= 12:
                line['words'].append({'text': text, 'x': x})
                placed = True
                break
        if not placed:
            lines.append({'y': y, 'h': h, 'words': [{'text': text, 'x': x}]})
            
    lines.sort(key=lambda l: l['y'])
    for l in lines:
        l['words'].sort(key=lambda w: w['x'])
        l['text'] = " ".join([w['text'] for w in l['words']])
    return lines

def process_image(path):
    img = cv2.imread(path)
    if img is None: return None
    
    symbols = extract_symbols(img)
    lines = get_text_lines(img)
    
    # Mana / Recharge
    mana = 0
    top_right = img[20:130, 520:650] if img.shape[1] > 600 else None
    if top_right is not None:
        try:
            num = pytesseract.image_to_string(top_right, config='--psm 10 -c tessedit_char_whitelist=0123456789').strip()
            if num.isdigit(): mana = int(num)
        except: pass

    # Difficulty
    challenges = sum(1 for p in symbols.get('challenge', []) if p[1] < 200)
    failures = sum(1 for p in symbols.get('failure', []) if p[1] < 200)
    blacks = sum(1 for p in symbols.get('black', []) if p[1] < 200)
    diff_str = ""
    if challenges > 0: diff_str += f"{challenges}c "
    if failures > 0: diff_str += f"{failures}f "
    if blacks > 0: diff_str += f"{blacks}b"
    diff_str = diff_str.strip()

    effect_rows = {}
    for sym_type in ['hammer', 'eagle', 'skull', 'comet', 'chaos']:
        for pt in symbols.get(sym_type, []):
            if pt[1] < 200: continue
            placed = False
            for ry in effect_rows.keys():
                if abs(ry - pt[1]) < 25:
                    effect_rows[ry][sym_type] = effect_rows[ry].get(sym_type, 0) + 1
                    placed = True
                    break
            if not placed:
                effect_rows[pt[1]] = {sym_type: 1}

    sorted_ys = sorted(effect_rows.keys())
    effects_data = []
    
    for i, y in enumerate(sorted_ys):
        next_y = sorted_ys[i+1] if i+1 < len(sorted_ys) else 9999
        row_text = [l['text'] for l in lines if l['y'] >= y - 15 and l['y'] < next_y - 15]
        desc = ' '.join(row_text)
        
        mapping = {'hammer': 'success', 'eagle': 'boon', 'skull': 'bane', 'comet': 'sigmarsComet', 'chaos': 'chaosStar'}
        
        for k, v in effect_rows[y].items():
            if k in mapping:
                effects_data.append({
                    "type": mapping[k],
                    "symbolAmount": v,
                    "description": f"<p>{desc}</p>"
                })
                break
                
    reqs_lines = [l['text'] for l in lines if l['y'] < (sorted_ys[0]-15 if sorted_ys else 9999) and l['y'] > 200]
    reqs_text = ' '.join(l for l in reqs_lines if len(l) > 4)

    return {
        "difficulty": diff_str,
        "recharge": mana,
        "requirements": f"<p>{reqs_text}</p>" if reqs_text else "",
        "effects_data": effects_data
    }

def main():
    print("Finding images...")
    images = []
    for root, dirs, files in os.walk("Warhammer rpg 3ed"):
        if "Careers" in root or "New" in root: continue
        for f in files:
            if f.lower().endswith(".jpg") or f.lower().endswith(".png"):
                images.append(os.path.join(root, f))
                
    print(f"Found {len(images)} images.")
    
    items = {}
    for i, img_path in enumerate(images):
        if i % 10 == 0:
            print(f"Processing {i}/{len(images)}...")
        base_name, face = clean_name(os.path.basename(img_path))
        folder = get_base_folder(img_path)
        
        data = process_image(img_path)
        if not data: continue
        
        if base_name not in items:
            items[base_name] = {
                "name": base_name,
                "type": "action" if folder == "Actions" else "ability",
                "_id": generate_id(),
                "folder": folder,
                "system": {
                    "conservative": {"effects": {}, "recharge": 0, "difficulty": ""},
                    "reckless": {"effects": {}, "recharge": 0, "difficulty": ""}
                }
            }
            
        target_sys = items[base_name]["system"]
        target_faces = ["conservative", "reckless"] if face == 'base' and items[base_name]["type"] == "action" else [face] if face != 'base' else ["conservative"]
            
        for f_key in target_faces:
            sys = target_sys[f_key]
            sys["difficulty"] = data["difficulty"]
            sys["recharge"] = data["recharge"]
            if data["requirements"]: sys["requirements"] = data["requirements"]
            
            eff_dict = {"success":[], "righteousSuccess":[], "boon":[], "bane":[], "chaosStar":[], "sigmarsComet":[], "delay":[], "exertion":[]}
            for eff in data["effects_data"]:
                eff_dict[eff["type"]].append({
                    "symbolAmount": eff["symbolAmount"],
                    "description": eff["description"]
                })
            sys["effects"] = eff_dict

    os.makedirs("packs/source/items", exist_ok=True)
    
    for name, item in items.items():
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        filename = f"{safe_name}_{item['_id']}.json"
        with open(os.path.join("packs/source/items", filename), "w") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
            
    print(f"Successfully rebuilt {len(items)} compendium JSON items!")

if __name__ == "__main__":
    main()
