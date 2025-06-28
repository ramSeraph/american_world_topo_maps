# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "Pillow",
# ]
# ///

import os
import re
import json
import time
import shutil
import zipfile
import subprocess
import xml.etree.ElementTree as ET
from multiprocessing import Pool, cpu_count

from pathlib import Path
from pprint import pprint

from PIL import Image

raw_dir = Path('data/kmzs/raw') 
inter_dir = Path('data/kmzs/inter')
export_dir = Path('export/kmzs/gtiffs')

raw_dir.mkdir(parents=True, exist_ok=True)
inter_dir.mkdir(parents=True, exist_ok=True)
export_dir.mkdir(parents=True, exist_ok=True)

def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        raise Exception(f'command {cmd} failed with exit code: {res.returncode}')

def create_cutline_from_geometry(geometry, file):
    
    with open(file, 'w') as f:
        cutline_data = {
            "type": "FeatureCollection",
            "name": "CUTLINE",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": geometry,
            }]
        }
        json.dump(cutline_data, f, indent=4)
 
def create_cutline(bbox, file):
    """
    Create a cutline GeoJSON file for the given bounding box.
    bbox format: [west, south, east, north]
    """
    west, south, east, north = bbox
    # Create polygon coordinates in lon,lat format
    polygon_coords = [[west, north], [east, north], [east, south], [west, south], [west, north]]

    geometry = {
        "type": "Polygon",
        "coordinates": [polygon_coords]
    }
    create_cutline_from_geometry(geometry, file)
    
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

# Recursively search for folders containing "_Ln_" in their name
def find_level_n_folders(element, n):
    level_n_tiles = []
    for folder in element.findall('.//kml:Folder', ns):
        name_elem = folder.find('kml:name', ns)
        if name_elem is not None and f'_L{n}_' in name_elem.text:
            # Extract ground overlay information
            ground_overlay = folder.find('kml:GroundOverlay', ns)
            if ground_overlay is not None:
                # Get the icon href (JPG filename)
                icon = ground_overlay.find('.//kml:href', ns)
                
                # Get the geographical bounds
                latlonbox = ground_overlay.find('kml:LatLonBox', ns)
                
                if icon is not None and latlonbox is not None:
                    # Extract coordinates
                    north = float(latlonbox.find('kml:north', ns).text)
                    south = float(latlonbox.find('kml:south', ns).text)
                    east = float(latlonbox.find('kml:east', ns).text)
                    west = float(latlonbox.find('kml:west', ns).text)
                    
                    tile_info = {
                        "name": name_elem.text,
                        "jpg_file": icon.text,
                        "geographical_coverage": {
                            "north": north,
                            "south": south,
                            "east": east,
                            "west": west
                        }
                    }
                    level_n_tiles.append(tile_info)

    return level_n_tiles


def parse_kml_for_level_n_tiles(kml_content, n):
    """
    Parse KML content and extract Level n JPG files with their geographical coverage.
    
    Args:
        kml_content (bytes): KML file content as bytes
        
    Returns:
        dict: JSON structure containing Level n tiles and their coverage
    """
    # Parse the XML from bytes
    root = ET.fromstring(kml_content)
    
    # Define the KML namespace
    
    # Find all folders with Level 4 in their name
    # Start the search from the root
    level_n_tiles = find_level_n_folders(root, n)

    
    # Sort tiles by name for consistent ordering
    level_n_tiles.sort(key=lambda x: x['name'])
    
    # Create the final JSON structure
    result = {
        "document_name": root.find('.//kml:Document/kml:name', ns).text if root.find('.//kml:Document/kml:name', ns) is not None else "Unknown",
        "level_n_tiles": level_n_tiles
    }
    
    return result



def convert_to_tiff(path, geometry, out_path):
    # open the zipfile and list the contents
    with zipfile.ZipFile(path, 'r') as z:
        files = list(z.namelist())
        pprint(files)

        if 'doc.kml' not in files:
            print(f'No doc.kml found in {path.name}')
            return

        # Read KML content directly from zip and parse it
        with z.open('doc.kml') as f:
            kml_content = f.read()

            
        # Parse the KML content using the existing function
        kml_data = parse_kml_for_level_n_tiles(kml_content, 4)
        if len(kml_data['level_n_tiles']) == 0:
            print(f'No Level 4 tiles found in {path.name}')
            kml_data = parse_kml_for_level_n_tiles(kml_content, 3)
        
        # Create output directory for this KMZ file
        output_dir = inter_dir / path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        doc_path = output_dir / 'doc.kml'
        doc_path.write_bytes(kml_content)

        main_cutline_file = output_dir / 'main_cutline.geojson'
        create_cutline_from_geometry(geometry, main_cutline_file)
        
        # Extract JPG files referenced in the KML data and process them
        tiff_files = []
        sample_file_name = None
        for tile in kml_data['level_n_tiles']:
            jpg_filename = tile['jpg_file']
            if jpg_filename in files:
                with z.open(jpg_filename) as jpg_file:
                    if sample_file_name is None:
                        sample_file_name = jpg_filename
                    jpg_filename = jpg_filename.lower()  # Ensure filename is lowercase
                    jpg_path = output_dir / jpg_filename
                    jpg_path.write_bytes(jpg_file.read())
                    print(f'Extracted {jpg_filename} to {jpg_path}')
                    
                    # Get image dimensions using Pillow
                    with Image.open(jpg_path) as img:
                        width, height = img.size

                    if width <= 1 or height <= 1:
                        print(f'Skipping {jpg_filename} due to invalid dimensions: {width}x{height}')
                        continue
                    
                    # Get geographical bounds
                    bounds = tile['geographical_coverage']
                    north, south = bounds['north'], bounds['south']
                    east, west = bounds['east'], bounds['west']
                    
                    # Create TIFF filename
                    # remove the extension from jpg_filename and replace with .tif
                    ext = jpg_filename.split('.')[-1]
                    if ext not in ['jpg', 'jpeg']:
                        # convert o jpg using pillow
                        img = Image.open(jpg_path)
                        img = img.convert('RGB')
                        jpg_filename = jpg_filename.replace(f'.{ext}', '.jpg')
                        jpg_path = output_dir / jpg_filename
                        ext = jpg_filename.split('.')[-1]
                        img.save(jpg_path, 'JPEG')

                    tiff_filename = jpg_filename.replace(f'.{ext}', '.tif')
    
                    tiff_path = output_dir / tiff_filename
                    
                    # Create GCP string with image dimensions
                    gcp_str = f'-gcp 0 0 {west} {north} -gcp {width} 0 {east} {north} -gcp {width} {height} {east} {south} -gcp 0 {height} {west} {south}'
                    
                    # Add GCPs and convert to TIFF
                    translate_cmd = f'gdal_translate {gcp_str} -a_srs "EPSG:4326" -of GTiff "{jpg_path}" "{tiff_path}"'
                    run_external(translate_cmd)
                    
                    # Create cutline file for this tile
                    #cutline_filename = tiff_filename.replace('.tif', '.cutline.geojson')
                    #cutline_path = output_dir / cutline_filename
                    #bbox = [west, south, east, north]
                    #create_cutline(bbox, cutline_path)
                    
                    # Create warped version using gdalwarp with target SRS EPSG:3857 and cutline
                    warped_filename = tiff_filename.replace('.tif', '.warped.tif')
                    warped_path = output_dir / warped_filename
                    
                    # Use same parameters as parse.py
                    cutline_options = f'-cutline "{main_cutline_file}" -cutline_srs "EPSG:4326" -crop_to_cutline --config GDALWARP_IGNORE_BAD_CUTLINE YES -wo CUTLINE_ALL_TOUCHED=TRUE'
                    warp_quality_config = {'COMPRESS': 'JPEG', 'JPEG_QUALITY': '75', 'TILED': 'YES'}
                    warp_quality_options = ' '.join([f'-co {k}={v}' for k, v in warp_quality_config.items()])
                    reproj_options = '-tps -r bilinear -t_srs "EPSG:3857"'
                    nodata_options = '-dstalpha'
                    perf_options = '-multi -wo NUM_THREADS=ALL_CPUS --config GDAL_CACHEMAX 1024 -wm 1024'
                    
                    warp_cmd = f'gdalwarp -overwrite {perf_options} {nodata_options} {reproj_options} {warp_quality_options} {cutline_options} "{tiff_path}" "{warped_path}"'
                    run_external(warp_cmd)
                    
                    tiff_files.append(str(warped_path))
                    print(f'Converted {jpg_filename} to {tiff_filename} with GCPs and warped to {warped_filename}')
            else:
                print(f'Warning: {jpg_filename} not found in {path.name}')
        
        # Create VRT file with all warped TIFF files
        if tiff_files:
            vrt_path = output_dir / f'{path.stem}.vrt'
            vrt_cmd = f'gdalbuildvrt "{vrt_path}" {" ".join([f'"{f}"' for f in tiff_files])}'
            run_external(vrt_cmd)

            #final_path = output_dir / 'final.tif'
            
            # Create final merged TIFF from VRT using gdal_translate (same as parse.py export_internal)
            creation_opts = '-co TILED=YES -co COMPRESS=JPEG -co JPEG_QUALITY=75 -co PHOTOMETRIC=YCBCR'
            creation_opts += '--config GDAL_PAM_ENABLED NO'
            mask_options = '--config GDAL_TIFF_INTERNAL_MASK YES -b 1 -b 2 -b 3 -mask 4'
            perf_options = '--config GDAL_CACHEMAX 512'
            final_cmd = f'gdal_translate {perf_options} {mask_options} {creation_opts} "{vrt_path}" "{out_path}"'
            run_external(final_cmd)
            
            #cutline_options = f'-cutline "{main_cutline_file}" -cutline_srs "EPSG:4326" -crop_to_cutline --config GDALWARP_IGNORE_BAD_CUTLINE YES -wo CUTLINE_ALL_TOUCHED=TRUE'
            #warp_cmd = f'gdalwarp {cutline_options} "{final_path}" "{out_path}"'
            #run_external(warp_cmd)
            print(f'Created final TIFF: {out_path}')
        
        return kml_data['document_name'], sample_file_name


def process_kmz_item(args):
    sheet_no, geometry, kmz_url = args
    
    kmz_path = raw_dir / f'{sheet_no}.kmz'
    out_file = Path('export/kmzs/gtiffs') / f'{sheet_no}.tif'
    
    print(f'Converting {kmz_path.name} to TIFF...')
    name, sample_file_name = convert_to_tiff(kmz_path, geometry, out_file)

    result = {
        'sheet_no': sheet_no,
        'sample_file': sample_file_name,
        'name': name,
        'url': kmz_url
    }
    
    shutil.rmtree(str(inter_dir / sheet_no))
    kmz_path.unlink()
         
    pid = os.getpid()
    # Write results to JSONL file
    with open(f'kmz-infos-{pid}.jsonl', 'a') as f:
        f.write(json.dumps(result) + '\n')


def main():
    data = json.loads(Path('index/JOGS_Maps_KMZ_Index.geojson').read_text())

    # Filter items that need processing
    process_args = []
    for item in data['features']:
        props = item['properties']
        sheet_no = props['TILE_NAME']
        sheet_no = sheet_no.strip().replace(' ', '_')

        kmz_path = raw_dir / f'{sheet_no}.kmz'
        out_file = export_dir / f'{sheet_no}.tif'

        # Ensure sheet_no is a valid tiff_filename
        html = props['SEE_MAP']
        # <a href="https://libgis.ku.edu/jogs/nt-25-02_1-ground.KMZ">NT 25-02</a>',
        match = re.search(r'href="([^"]+)"', html)
        if not match:
            print(f'No href found in SEE_MAP for {sheet_no}, skipping.')
            continue

        kmz_url = match.group(1)


        if out_file.exists():
            print(f'Skipping {sheet_no}, already exists.')
            continue

        if not kmz_path.exists():
            continue
        
        if item['geometry'] is None:
            print(f'No geometry for {sheet_no}, skipping.')
            continue

        process_args.append((sheet_no, item['geometry'], kmz_url))
    
    # Use multiprocessing to process KMZ files in parallel
    if process_args:
        num_processes = min(cpu_count(), len(process_args))
        print(f'Processing {len(process_args)} KMZ files using {num_processes} processes...')
        
        with Pool(processes=num_processes) as pool:
            pool.map(process_kmz_item, process_args)

if __name__ == '__main__':      
    main()





