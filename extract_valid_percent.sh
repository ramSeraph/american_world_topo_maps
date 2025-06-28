#!/bin/bash

# Script to extract STATISTICS_VALID_PERCENT from all GeoTIFF files
# in export/kmzs/gtiffs directory

echo "File,STATISTICS_VALID_PERCENT"

for file in export/kmzs/gtiffs/*.tif; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        valid_percent=$(gdalinfo -stats "$file" | grep "STATISTICS_VALID_PERCENT" | head -1 | cut -d'=' -f2)
        echo "$filename,$valid_percent"
    fi
done
