
wget -P data https://maps.lib.utexas.edu/maps/onc/

uv run filter_links.py data/index.html ONC > data/all_links.jsonl

uv run download_pages.py
uv run parse_pages.py
