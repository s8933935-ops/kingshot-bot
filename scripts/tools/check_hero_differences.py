import re
from parse_heroes_truth import heroes as official_heroes

# Build official dict
off_map = {}
for h in official_heroes:
    key = h['name'].lower().replace('&', '').replace(' ', '-').replace('--', '-')
    off_map[key] = h
    # also by raw name
    off_map[h['name'].lower()] = h

# Read web_tierlist/index.html heroesData
with open(r'C:\Users\s8933\Downloads\PvPジョイナー動画\web_tierlist\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Parse heroesData
import json
start_idx = html.find('const heroesData = [')
end_idx = html.find('];', start_idx)
block = html[start_idx:end_idx+2]

# Let's extract each object
pattern = r"{\s*id:\s*'([^']+)',\s*name:\s*'([^']+)',\s*origName:\s*'([^']+)',\s*tier:\s*'([^']+)',\s*gen:\s*'([^']+)',\s*troop:\s*'([^']+)',\s*troopName:\s*'([^']+)'"
matches = re.findall(pattern, block)

print(f"Parsed {len(matches)} heroes from index.html\n")
print(f"{'ID':<12} | {'Name':<10} | {'Current Gen':<12} | {'Official Gen':<16} | {'Current Troop':<14} | {'Official Troop':<14} | Status")
print("-" * 95)

troop_map_ja = {
    'Infantry': ('infantry', '歩兵'),
    'Cavalry': ('cavalry', '騎兵'),
    'Archer': ('archer', '弓兵')
}

discrepancies = []

for m in matches:
    hid, hname, horig, htier, hgen, htroop, htroopname = m
    # find in official
    off = None
    for k, v in off_map.items():
        if k in hid or hid in k or horig.lower() in k or k in horig.lower():
            off = v
            break
    
    if off:
        off_gen_str = off['section']
        off_troop_str = off['troop']
        correct_troop, correct_troop_ja = troop_map_ja.get(off_troop_str, ('', ''))
        
        gen_diff = False
        troop_diff = False
        
        # Check Gen
        if 'gen-8' in off['sec_id'] and 'Gen 8' not in hgen: gen_diff = True
        elif 'gen-7' in off['sec_id'] and 'Gen 7' not in hgen: gen_diff = True
        elif 'gen-6' in off['sec_id'] and 'Gen 6' not in hgen: gen_diff = True
        elif 'gen-5' in off['sec_id'] and 'Gen 5' not in hgen: gen_diff = True
        elif 'gen-4' in off['sec_id'] and 'Gen 4' not in hgen: gen_diff = True
        elif 'gen-3' in off['sec_id'] and 'Gen 3' not in hgen: gen_diff = True
        elif 'gen-2' in off['sec_id'] and 'Gen 2' not in hgen: gen_diff = True
        elif 'gen-1' in off['sec_id'] and 'Gen 1' not in hgen: gen_diff = True
        elif 'epic' in off['sec_id'] and 'SR' not in hgen and 'Epic' not in hgen: gen_diff = True
        
        if htroop != correct_troop:
            troop_diff = True
            
        status = "OK"
        if gen_diff or troop_diff:
            status = "MISMATCH: "
            if gen_diff: status += f"[Gen: {hgen} -> {off_gen_str}] "
            if troop_diff: status += f"[Troop: {htroopname} -> {correct_troop_ja}] "
            discrepancies.append((hid, hname, hgen, off_gen_str, htroopname, correct_troop_ja))
            
        print(f"{hid:<12} | {hname:<10} | {hgen:<12} | {off_gen_str:<16} | {htroopname:<14} | {correct_troop_ja:<14} | {status}")
    else:
        print(f"{hid:<12} | {hname:<10} | {hgen:<12} | {'NOT FOUND':<16} | {htroopname:<14} | {'?':<14} | NOT FOUND")

print(f"\nTotal Discrepancies: {len(discrepancies)}")
