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
comm -13 mapstor.txt pcl.txt > pcl_to_process.txt
cat mapstor/bad_sheets.txt >> pcl_to_process.txt

# 6. now parse the pcl files
# only sheets which are not available in mapstor will be processed
uv run parse_pcl.py

# 7. now tile the georeferenced files
GDAL_VERSION=$(gdalinfo --version | cut -d"," -f1 | cut -d" " -f2)
uvx --with numpy --with pillow --with gdal==$GDAL_VERSION --from topo-map-processor tile --tiles-dir export/tiles --tiffs-dir export/gtiffs --max-zoom 10 --name ONC --description "ONC 1:1m maps" --attribution-file attribution.txt

# 8. finally generate the pmtiles mosaic
uvx --from pmtiles-mosaic partition --from-source export/tiles --to-pmtiles export/pmtiles/ONC.pmtiles

# 9. upload the pmtiles file to github
gh release upload onc-pmtiles export/pmtiles/* --clobber

# 10. upload the georef files to github
uvx --from gh-release-tools upload-to-release -r onc-georef -d export/gtiffs -e .tif
uvx --from gh-release-tools generate-lists -r onc-georef -e .tif

# 11. upload the orig files to github
uvx --from gh-release-tools upload-to-release -r onc-orig -d data/raw -e .gif -e .map

mkdir pcl/to_push
cat pcl_to_process.txt | xargs -I {} cp pcl/data/raw/{}.jpg pcl/to_push/
uvx --from gh-release-tools upload-to-release -r onc-orig -d pcl/to_push -e .jpg
rm -rf pcl/to_push

uvx --from gh-release-tools generate-lists -r onc-orig -e .jpg -e .gif -e .map





