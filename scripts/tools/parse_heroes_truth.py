from bs4 import BeautifulSoup
import json

with open(r'C:\Users\s8933\.gemini\antigravity\brain\08f778a2-d8b6-4f27-8c8e-eefebc4fd5a2\.system_generated\steps\622\content.md', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

sections = soup.find_all('section', class_='gen-section')
heroes = []
for sec in sections:
    sec_id = sec.get('id', '')
    sec_title = sec.find('h2').get_text(strip=True) if sec.find('h2') else sec_id
    tiles = sec.find_all('a', class_='hero-tile')
    for t in tiles:
        if 'hero-tile-more' in t.get('class', []):
            continue
        name = t.find('div', class_='hero-tile-name').get_text(strip=True) if t.find('div', class_='hero-tile-name') else ''
        rarity = t.get('data-rarity', '')
        type_span = t.find('span', class_='troop-type-icon')
        troop = ''
        if type_span:
            troop = type_span.get('title', '')
        heroes.append({'section': sec_title, 'sec_id': sec_id, 'name': name, 'rarity': rarity, 'troop': troop})

print(f"Total extracted heroes: {len(heroes)}")
for h in heroes:
    print(f"{h['sec_id']} | {h['name']} | {h['rarity']} | {h['troop']}")
