#!/bin/bash

# 1. first download and process the pcl files  
cd pcl
./steps.sh
cd -

# 2. now download and process the mapstor files
cd mapstor
./steps.sh
cd -

# 3. parse the mapstor files first
# add special handling to mapstor/special_cases.json as required
# collect the unprocessable files to mapstor/bad_sheets.txt
uv run parse_mapstor.py

# 4. remove the sheets listed in bad_sheets.txt from the mapstor data
cat mapstor/bad_files.txt | xargs -I {} rm mapstor/data/raw/{}.gif
cat mapstor/bad_files.txt | xargs -I {} rm mapstor/data/raw/{}.map

# 5. collect the list of files which need to be processed from pcl
# this will be used later
comm -13 mapstor/data/sheet_ids.txt pcl/data/sheet_ids.txt > pcl_to_process.txt
cat mapstor/bad_sheets.txt >> pcl_to_process.txt

# 6. now parse the pcl files
# only sheets which are not available in mapstor will be processed
uv run parse_pcl.py

# 7. upload the georef files to github
uvx --from gh-release-tools upload-to-release -r tpc-georef -d export/gtiffs -e .tif
uvx --from gh-release-tools generate-lists -r tpc-georef -e .tif
uvx --from topo-map-processor collect-bounds --bounds-dir export/bounds --output-file export/bounds.geojson
gh release upload tpc-georef export/bounds.geojson

# 8. upload the orig files to github
uvx --from gh-release-tools upload-to-release -r tpc-orig -d data/raw -e .gif -e .map

mkdir pcl/data/to_push
cat pcl_to_process.txt | xargs -I {} cp pcl/data/raw/{}.jpg pcl/data/to_push/
uvx --from gh-release-tools upload-to-release -r tpc-orig -d pcl/data/to_push -e .jpg
rm -rf pcl/data/to_push
rm pcl_to_process.txt

uvx --from gh-release-tools generate-lists -r tpc-orig -e .jpg -e .gif -e .map


# 9. now tile the georeferenced files
GDAL_VERSION=$(gdalinfo --version | cut -d"," -f1 | cut -d" " -f2)
uvx --with numpy --with pillow --with gdal==$GDAL_VERSION --from topo-map-processor tile --tiles-dir export/tiles --tiffs-dir export/gtiffs --max-zoom 10 --name TPC --description "TPC 1:500k maps" --attribution-file attribution.txt

# 10. finally generate the pmtiles mosaic
uvx --from pmtiles-mosaic partition --from-source export/tiles --to-pmtiles export/pmtiles/TPC.pmtiles

# 11. upload the pmtiles file to github and add tiled list file
gh release upload tpc-pmtiles export/pmtiles/*
gh release download tpc-georef -p listing_files.csv 
gh release upload tpc-pmtiles listing_files.csv 
rm listing_files.csv




