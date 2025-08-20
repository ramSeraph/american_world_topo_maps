from pathlib import Path
import json

info_map = {
    "Asia_South_250k_U502": {
        "id": "Sheet_no_1",
        "url": "Scanned_map"
    },
    "Burma_250k_U542": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "China_250k_L500": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "China_Manchuria_250k_L542": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Asia_Indochina_Thailand_L509": {
        "id": "Sheet_no_1",
        "url": "Scanned_map"
    },
    "Philippines_250k_S501": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "New_Guinea_250k_T504": {
        "id": "Sheet_no_1",
        "url": "Scanned_map"
    },
    "Indonesia_250k_T503": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Asia_Southwest_250k_K502": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Japan_250k_L506": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Korea_250k_L552": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Marianas_Islands_250k_W543": {
        "id": "Sheet_no",
        "url": "Scan_avail_yes"
    },
    "Mongolia_250k_L522": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Siberia_Central_USSR_250k_N503": {
        "id": "Sheet_no",
        "url": "Scan_link"
    },
    "Siberia_Eastern_USSR_250k_N504": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Siberia_West_USSR_250k_N502": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
    "Taiwan_250k_L594": {
        "id": "Sheet_no",
        "url": "Scanned_map"
    },
}

paths = list(Path('index/250k').glob('*.geojson'))
paths.sort()

items = []
by_sheet_num = {}

for p in paths:
    name = p.stem.strip()
    print(name)
    info = info_map[name]

    data = json.loads(p.read_text())
    features = data.get('features', [])
    for feat in features:
        props = feat.get('properties', {})

        id_field = info['id']
        url_field = info['url']

        sheet_num = props[id_field].strip()
        sheet_num = sheet_num.replace(' ', '_')
        url = props[url_field]

        if sheet_num in by_sheet_num:
            continue

        by_sheet_num[sheet_num] = True

        props['canon_id'] = sheet_num
        props['canon_url'] = url
        props['canon_series'] = name

        items.append(feat)

data = { 'type': 'FeatureCollection', 'features': items }

Path('index_wgs84.geojson').write_text(json.dumps(data))





