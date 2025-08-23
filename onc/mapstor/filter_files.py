import csv
import json
from pathlib import Path

def should_skip(fname):
    if fname.endswith('/'):
        return True
    if fname.endswith('--coverage.gif'):
        return True
    if fname.endswith('.kml'):
        return True
    if fname.endswith('.html'):
        return True
    if fname.endswith('mapstor.gif'):
        return True

    return False

def parse_id(id):
    id = id.upper()
    if len(id) != 3:
        raise ValueError(f"Invalid ID length: {id}")
    return id


all_files = {}
with open('data/zip_files.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        fname = row['filename']
        url = row['url']
        if should_skip(fname):
            continue
        all_files[fname] = { 'url': url }

by_id = {}
for fname, data in all_files.items():
    if not fname.endswith('.gif'):
        continue

    parts = fname.split('/')
    if len(parts) < 2:
        continue
    fname = parts[1]
    parts = fname.split('--')
    date_part_idx = -1
    for i,part in enumerate(parts):
        if part.startswith('(') and part.endswith(')'):
            date_part_idx = i
            break
    if date_part_idx < 0:
        print(f"Skipping {fname} as it has no date part")
        continue

    date_part = parts[date_part_idx]
    year = int(date_part[1:-1])  # Remove parentheses
    id = parts[date_part_idx - 1]  # The part before the date part
    id = parse_id(id)
    if id in by_id:
        prev_year = by_id[id]['year']
        if prev_year > year:
            print(f"Skipping {fname} as it is older than {by_id[id]['filename']} ({prev_year})")
            continue
    by_id[id] = data
    data['year'] = year
    data['filename'] = fname

print(f"Found {len(by_id)} unique IDs")

Path('data/sheet_map.json').write_text(json.dumps(by_id, indent=2))
