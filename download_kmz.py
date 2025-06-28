# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
# ]
# ///

import re
import json

from pathlib import Path
from pprint import pprint

import requests

raw_dir = Path('data/kmzs/raw') 

def download_file(url, out_path):
    print(f'Downloading {url} to {out_path}')
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad responses

    out_path.write_bytes(response.content)
    
    print(f'Download completed: {out_path}')


def main():
    data = json.loads(Path('index/JOGS_Maps_KMZ_Index.geojson').read_text())

    for item in data['features']:
        props = item['properties']
        #pprint(props)
        sheet_no = props['TILE_NAME']
        sheet_no = sheet_no.strip().replace(' ', '_')

        # Ensure sheet_no is a valid tiff_filename
        html = props['SEE_MAP']
        # <a href="https://libgis.ku.edu/jogs/nt-25-02_1-ground.KMZ">NT 25-02</a>',
        match = re.search(r'href="([^"]+)"', html)
        if not match:
            print(html)
            print(f'No href found in SEE_MAP for {sheet_no}, skipping.')
            continue

        kmz_url = match.group(1)

        final_path = Path('export/kmzs/gtiffs/') / f'{sheet_no}.tif'
        if final_path.exists():
            continue
        kmz_path = raw_dir / f'{sheet_no}.kmz'
        if not kmz_path.exists():
            download_file(kmz_url, kmz_path)
 
if __name__ == '__main__':      
    main()

