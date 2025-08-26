
# 1. Download the index page and filter links 
wget -P data https://maps.lib.utexas.edu/maps/tpc/

# 2. Filter links to the images from the index page and save to a JSONL file
uv run filter_links.py data/index.html TPC > data/all_links.jsonl

# 3. get metadata from the links file and create the data/sheet_map.json file
uv run parse_pages.py

# get the list of all sheet ids
cat data/sheet_map.json| jq -r '. | keys[]' | sort > data/sheet_ids.txt

# 4. Download all the files
uv run download_files.py data/sheet_ids.txt

# 5. use surya to get the OCR the sheets.. too slow on my machine.. ran it on GPU in vast.ai
uv run surya_text.py

# 6. Extract the projections from the extracted text to data/proj_map.json
uv run collect_projections.py

# 7. Check for unique projection infos, usually a sign of OCR errors
uv run check_projs.py

# 7. Manually georeference the missing ones
