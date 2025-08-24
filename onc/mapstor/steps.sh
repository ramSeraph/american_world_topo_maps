#!/bin/bash

set -e

# 1. get list of ids from internet archive
uvx --from internetarchive ia search -i "collection:topographic-maps" > data/mapstor_ids.txt

# 2. filter for onc maps only
cat data/mapstor_ids.txt| grep "\-\-onc\-\-" > data/onc_ids.txt

# 3. get list of zip files for each id
cat data/onc_ids.txt | xargs -I {} uvx --from internetarchive ia list {} -l | grep "zip$" > data/zip_urls.txt

# 4. collect the list of files in each zip file
uv run list_zip_contents.py data/zip_urls.txt data/zip_files.csv

# 5. filter for gif and map files only and create a metadata file at data/sheet_map.json
uv run filter_files.py

# 6. download the files by reading the zip files remotely
uv run download_files.py

# 7. collect the sheet ids for th sheet map
cat data/sheet_map.json| jq -r '. | keys[]' | sort > sheet_ids.txt


