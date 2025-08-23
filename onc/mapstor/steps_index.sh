
set -e
# getting the index files
wget -P data/ https://archive.org/download/all--maps/all--maps.kmz

cd data
ogr2ogr -f GEOJSONSEQ "all--maps.geojsonl" "all--maps.kmz"
rm "all--maps.kmz"

# for a full run
#cat "all--maps.geojsonl" | jq -r .properties.Name | cut -d"-" -f1,3,5 | sort -u | awk '{gsub(/-/,"--"); print}' > sets.txt
#cat sets.txt | xargs -I {} sh -c "cat all--maps.geojsonl| jq  --indent 0 'select(.properties.Name | startswith(\"{}\"))' > {}.geojsonl"

# for just jog
cat "all--maps.geojsonl" | jq  --indent 0 'select(.properties.Name | startswith("en--onc--001m"))' > "en--onc--001m.geojsonl"

rm "all--maps.geojsonl"
cd - 

mv "data/en--onc--001m.geojsonl" ../index/


