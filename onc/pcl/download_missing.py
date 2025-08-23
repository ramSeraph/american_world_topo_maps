import requests
import json

from pathlib import Path

with open('data/sheet_map.json', 'r') as f:
    sheet_map = json.loads(f.read())

with open('diff.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        sno = line.strip()
        file = Path(f'data/raw/{sno}.jpg')
        if file.exists():
            continue
        url = sheet_map.get(sno)['url']
        print(sno, url)
        resp = requests.get(url)
        resp.raise_for_status()
        with open(file, 'wb') as f:
            f.write(resp.content)
