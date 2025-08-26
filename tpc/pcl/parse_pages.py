# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bs4",
# ]
# ///


import re
from bs4 import BeautifulSoup
from pathlib import Path
from pprint import pprint

def parse_link_text(link_text):
    match = re.search(r'(?P<block1>[A-Z])[\-]+(?P<block2>\d+)\-?(?P<block3>[A-Z])', link_text, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Could not parse link text: {link_text}")
    g = match.groupdict()
    sheet_no = f'{g["block1"]}{int(g["block2"]):02d}-{g["block3"]}'
    if sheet_no == 'G18-R':
        sheet_no = 'G18-D'
    return sheet_no 


def parse_sibling_text(sibling_text):
    # (10.5 MB)
    match = re.search(r'\(\s*(?P<size>[\d\.]+)?\s*(?P<unit>MB|KB)\s*\)', sibling_text, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Could not parse sibling text: {sibling_text}")
    g = match.groupdict()
    size = None
    if g['size'] is not None:
        size = float(g['size'])
        if g['unit'].upper() == 'MB':
            pass
        elif g['unit'].upper() == 'KB':
            size = size / 1024  # Convert KB to bytes
        else:
            raise ValueError(f"Unknown unit in sibling text: {g['unit']}")
    year = None
    matches = re.finditer(r'\b(?P<year>\d{4})\b', sibling_text)
    for match in matches:
        year = int(match.group('year'))
    return size, year

def parse_html_file(path):
    sheet_map = {}
    html = path.read_text()
    dom = BeautifulSoup(html, 'html.parser')
    uls = dom.find_all('ul')
    usable_ul_found = False
    already_seen = set()
    for ul in uls:
        lis = ul.find_all('li')
        if len(lis) == 0:
            continue
        usable_ul_found = True
        for li in lis:
            links = li.find_all('a')
            for link in links:
                if link.has_attr('href'):
                    href = link['href']
                    if href in already_seen:
                        continue
                    already_seen.add(href)
                    link_text = link.get_text(strip=True)
                    if link_text.lower().find('Clickable map') != -1:
                        continue
                    next_sibling = link.next_sibling
                    if next_sibling:
                        if next_sibling.name:
                            sibling_text = next_sibling.get_text(strip=True)
                        else:
                            sibling_text = next_sibling.strip()

                    size, year = parse_sibling_text(sibling_text)
                    sheet_no = parse_link_text(link_text)
                    sheet_map[sheet_no] = { 'url': href, 'text': sibling_text, 'link_text': link_text, 'size_in_mb': size, 'year': year }
                    print(sheet_no)
                    pprint(sheet_map[sheet_no])
    return sheet_map

path = Path('data/index.html')
sheet_map = parse_html_file(path)
pprint(sheet_map)

with open('data/sheet_map.json', 'w') as f:
    import json
    json.dump(sheet_map, f, indent=4)
