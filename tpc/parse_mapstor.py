# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "topo-map-processor[parse]",
#     "ozi-map",
# ]
#
# [tool.uv.sources]
# ozi-map = { git = "https://github.com/wladich/ozi_map.git" }
# ///


import os
import json
import traceback
from pathlib import Path
from pprint import pprint

import cv2
import numpy as np
from PIL import Image
from pyproj import Transformer, CRS

from topo_map_processor.processor import TopoMapProcessor

from ozi_map import ozi_reader

def get_mids(polygon):
    """
    Calculate the center of a polygon defined by a list of (x, y) tuples.
    """

    lons = [point[0] for point in polygon]
    lats = [point[1] for point in polygon]
    lons = [lon if lon > 0 or lon > -90 else lon + 360 for lon in lons]  # Normalize longitudes to [0, 360)
    max_lon = max(lons)
    min_lon = min(lons)
    mid_lon = (max_lon + min_lon) / 2
    mid_lon = mid_lon if mid_lon <= 180 else mid_lon - 360  # Normalize to [-180, 180)

    max_lat = max(lats)
    min_lat = min(lats)
    mid_lat = (max_lat + min_lat) / 2

    return mid_lon, mid_lat

def get_res(ul, ur, ll, w, h):
    ul_ur_xdelta_square = (ul[0] - ur[0])**2
    ul_ur_ydelta_square = (ul[1] - ur[1])**2

    ul_ll_xdelta_square = (ul[0] - ll[0])**2
    ul_ll_ydelta_square = (ul[1] - ll[1])**2

    # x_res_square, y_res_square  need to be calculated where
    # (x_res_square * proj_ul_ur_xdelta_square) + (y_res_square * proj_ul_ur_ydelta_square) = w ** 2
    # (x_res_square * proj_ul_ll_xdelta_square) + (y_res_square * proj_ul_ll_ydelta_square) = h ** 2
    # solve for x_res_square, y_res_square
    # (x_res_square * proj_ul_ur_xdelta_square * proj_ul_ll_xdelta_square) + (y_res_square * proj_ul_ur_ydelta_square * proj_ul_ll_xdelta_square) = (w ** 2) * proj_ul_ll_xdelta_square
    # (x_res_square * proj_ul_ll_xdelta_square * proj_ul_ur_xdelta_square) + (y_res_square * proj_ul_ll_ydelta_square * proj_ul_ur_xdelta_square) = (h ** 2) * proj_ul_ur_xdelta_square

    above = (((w ** 2) * ul_ll_xdelta_square) - ((h ** 2) * ul_ur_xdelta_square)) 
    below = ((ul_ur_ydelta_square * ul_ll_xdelta_square) - (ul_ll_ydelta_square * ul_ur_xdelta_square))
    y_res_square = above / below

    x_res_square = ((w ** 2) - (y_res_square * ul_ur_ydelta_square)) / ul_ur_xdelta_square

    return x_res_square, y_res_square



class TPCMapstorProcessor(TopoMapProcessor):

    def __init__(self, filepath, extra, index_box, index_properties, projinfo=None, id_override=None):
        super().__init__(filepath, extra, index_box, index_properties)
        self.id_override = id_override
        self.mapfile_processed = False
        self.mapfile_title = None
        self.crs_proj = None
        self.ozi_gcps = None
        self.ozi_cutline = None
        self.ozi_cutline_pixels = None
        self.jpeg_export_quality = extra.get('jpeg_export_quality', 75)
        self.warp_jpeg_quality = 100
        self.projinfo = projinfo
        self.cutline_override = extra.get('cutline_override', None)
        self.corner_gcps = extra.get('corner_gcps', None)
        self.same_proj_resolution = extra.get('same_proj_resolution', None)
        self.inset_pixel_cutlines = extra.get('inset_pixel_cutlines', None)
        self.inpaint_color = extra.get('inpaint_color', (255, 255, 255))

    def get_id(self):
        if self.id_override is not None:
            return self.id_override
        return self.super().get_id()

    def get_original_pixel_coordinate(self, p):
        return p

    def get_gcps(self, pre_rotated=False):
        if self.corner_gcps is not None:
            gcps = []
            for gcp in self.corner_gcps:
                gcps.append([(gcp['x'], gcp['y']),
                             (gcp['lon'], gcp['lat'])])
            return gcps

        self.process_map_file()
        if self.ozi_gcps is None:
            raise ValueError("GCPs not available")

        gcps = []
        for ozi_gcp in self.ozi_gcps:
            if ozi_gcp['type'] != 'latlon':
                raise ValueError(f"Unsupported GCP type: {ozi_gcp['type']}")

            pixel = ozi_gcp['pixel']
            ref = ozi_gcp['ref']
            gcps.append([(pixel['x'], pixel['y']),
                         (ref['x'], ref['y'])])
        return gcps

    def get_sheet_ibox(self):
        if self.cutline_override is not None:
            return self.cutline_override

        if self.corner_gcps is not None:
            corners = []
            for gcp in self.corner_gcps:
                corners.append((gcp['lon'], gcp['lat']))
            corners = corners + [corners[0]]
            return corners

        return self.ozi_cutline + [
            self.ozi_cutline[0]  # Close the polygon
        ]

    def get_corners(self, pre_rotated=False):
        self.process_map_file()
        if self.cutline_override is not None:
            gcps = self.get_gcps()
            transformer = self.get_transformer_from_gcps(gcps)
            corners = []
            for corner in self.cutline_override:
                x, y = transformer.rowcol(corner[0], corner[1])
                corners.append((x, y))
            return corners[:-1]

        if self.corner_gcps is not None:
            corners = []
            for gcp in self.corner_gcps:
                corners.append((gcp['x'], gcp['y']))
            return corners

        corners = self.ozi_cutline_pixels
        return corners

    def get_same_proj_resolution(self):
        gcps = self.get_gcps()

        crs = CRS.from_proj4(self.get_crs_proj())
        geog_crs = crs.geodetic_crs
        transformer = Transformer.from_crs(geog_crs, crs, always_xy=True)
        projected_gcps = []
        for gcp in gcps:
            corner = gcp[0]
            idx    = gcp[1]
            projected_idx = transformer.transform(idx[0], idx[1])
            projected_gcps.append((corner, projected_idx))

        proj_transformer = self.get_transformer_from_gcps(projected_gcps)
        full_img = self.get_full_img()
        h, w = full_img.shape[:2]
        corners = [
            (0, 0),
            (w, 0),
            (w, h),
            (0, h)
        ]
        projected_corners = [proj_transformer.xy(corner[1], corner[0]) for corner in corners]

        proj_ul = projected_corners[0]
        proj_ll = projected_corners[3]
        proj_ur = projected_corners[1]

        x_res_square, y_res_square = get_res(proj_ul, proj_ur, proj_ll, w, h)
        print(f'{x_res_square=}, {y_res_square=}')
        if x_res_square < 0 or y_res_square < 0:
            raise Exception(f"Negative resolution squared values: {x_res_square}, {y_res_square}")
            #proj_ul = [proj_ul[1], proj_ul[0]] 
            #proj_ll = [proj_ll[1], proj_ll[0]] 
            #proj_ur = [proj_ur[1], proj_ur[0]]
            #x_res_square, y_res_square = get_res(proj_ul, proj_ur, proj_ll, w, h)

        # TODO: how is this possible?
        #if x_res_square < 0:
        #    x_res_square = y_res_square
        #if y_res_square < 0:
        #    y_res_square = x_res_square

        return (1/(x_res_square**0.5), 1/(y_res_square**0.5))


    #def get_full_pixel_cutline(self, pre_rotated=False):
    #    self.process_map_file()
    #    if self.ozi_cutline is None:
    #        raise ValueError("Cutline not available")

    #    return self.ozi_cutline_pixels + [
    #        self.ozi_cutline_pixels[0]  # Close the polygon
    #    ]

    def export_bounds_file(self):
        bounds_dir = self.get_bounds_dir()

        bounds_file = bounds_dir.joinpath(f'{self.get_id()}.geojsonl')
        if bounds_file.exists():
            print(f'{bounds_file} exists.. overwriting')
            bounds_file.unlink()

        self.ensure_dir(bounds_dir)

        workdir = self.get_workdir()
        cutline_file = workdir.joinpath('cutline.geojson')

        self.run_external(f'ogr2ogr -t_srs EPSG:4326 -s_srs EPSG:4326 -f GeoJSONSeq {str(bounds_file)} {cutline_file}')

    def inpaint_insets(self, img, inset_pixel_cutlines, inpaint_color):
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        for inset_pixel_cutline in inset_pixel_cutlines:
            print(f'filling in inset with pixel cutline: {inset_pixel_cutline}')
            # Create a mask for the inset area
            mask = np.zeros(cv_img.shape[:2], dtype=np.uint8)
            pts = np.array([inset_pixel_cutline], dtype=np.int32)
            cv2.fillPoly(mask, pts, 255)
            # fill the area in cv_img with inpaint_color
            cv_img[mask == 255] = inpaint_color

        inpainted_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(inpainted_img)

    def process_map_file(self):
        if self.mapfile_processed:
            return
        map_filepath = self.filepath.with_suffix('.map')
        map_data = ozi_reader.read_ozi_map(open(map_filepath, 'rb'))

        self.index_properties['maptitle'] = map_data.get('title', '')

        #datum = map_data['datum']
        #if datum == 'WGS 84':
        #    self.crs_proj = 'EPSG:4326'
        #else:
        #    raise ValueError(f"Unsupported datum: {datum}")

        self.ozi_gcps = map_data['gcps']

        self.ozi_cutline = map_data['cutline']
        print(f"Cutline: {self.ozi_cutline}")
        self.ozi_cutline_pixels = map_data['cutline_pixels']

        self.mapfile_processed = True

    def rotate(self):

        # no rotation.. only convert

        workdir = self.get_workdir()

        full_img_path = workdir / 'full.jpg'

        if full_img_path.exists():
            return

        self.ensure_dir(workdir)

        img = Image.open(self.filepath)
        rgb_img = img.convert('RGB')
        if self.inset_pixel_cutlines is not None:
            rgb_img = self.inpaint_insets(rgb_img, self.inset_pixel_cutlines, self.inpaint_color)

        rgb_img.save(full_img_path, format='JPEG', subsampling=0, quality=100)

    def georeference(self):
        workdir = self.get_workdir()

        georef_file = workdir.joinpath('georef.tif')
        final_file  = workdir.joinpath('final.tif')
        if georef_file.exists() or final_file.exists():
            print(f'{georef_file} or {final_file} exists.. skipping')
            return

        from_file = self.get_full_file_path()

        crs_proj = self.get_crs_proj()

        gcps = self.get_gcps()

        crs = CRS.from_proj4(self.get_crs_proj())
        geog_crs = crs.geodetic_crs
        transformer = Transformer.from_crs(geog_crs, crs, always_xy=True)
        projected_gcps = []
        for gcp in gcps:
            corner = gcp[0]
            idx    = gcp[1]
            projected_idx = transformer.transform(idx[0], idx[1])
            projected_gcps.append((corner, projected_idx))

        gcp_str = ''
        for gcp in projected_gcps:
            corner = gcp[0]
            idx    = gcp[1]
            gcp_str += f' -gcp {corner[0]} {corner[1]} {idx[0]} {idx[1]}'
        
        creation_options = '-co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2' 
        perf_options = '--config GDAL_CACHEMAX 128 --config GDAL_NUM_THREADS ALL_CPUS'

        self.ensure_dir(workdir)
        translate_cmd = f'gdal_translate {creation_options} {perf_options} {gcp_str} -a_srs "{crs_proj}" -of GTiff {str(from_file)} {str(georef_file)}' 
        self.run_external(translate_cmd)

    def first_warp(self):
        workdir = self.get_workdir()
        warped_file = workdir.joinpath('warped.tif')
        if warped_file.exists():
            print(f'{warped_file} exists.. skipping')
            return

        georef_file = workdir.joinpath('georef.tif')

        self.ensure_dir(workdir)
        img_quality_config = {
            'COMPRESS': 'DEFLATE',
            #'COMPRESS': 'JPEG',
            'PREDICTOR': '2',
            #'PHOTOMETRIC': 'YCBCR',
            #'JPEG_QUALITY': self.warp_jpeg_quality,
            'TILED': 'YES',
            'BIGTIFF': 'IF_SAFER',
        }

        warp_quality_options = ' '.join([ f'-co {k}={v}' for k,v in img_quality_config.items() ])

        if self.same_proj_resolution is None:
            res = self.get_same_proj_resolution()
            FACTOR = 0.5
            size_options = f'-tr {res[0]*FACTOR} {res[1]*FACTOR}'
        elif self.same_proj_resolution == 'auto':
            size_options = ''
        else:
            res = self.same_proj_resolution
            size_options = f'-tr {res[0]} {res[1]}'

        crs_proj = self.get_crs_proj()
        reproj_options = f'-tps {size_options} -r bilinear -t_srs "{crs_proj}" -s_srs "{crs_proj}"' 
        #nodata_options = '-dstnodata 0'
        nodata_options = '-dstalpha'
        perf_options = '-multi -wo NUM_THREADS=ALL_CPUS --config GDAL_CACHEMAX 1024 -wm 1024' 

        warp_cmd = f'gdalwarp -overwrite {perf_options} {nodata_options} {reproj_options} {warp_quality_options} {str(georef_file)} {str(warped_file)}'
        self.run_external(warp_cmd)


    def warp(self):
        workdir = self.get_workdir()

        final_file = workdir.joinpath('final.tif')
        if final_file.exists():
            print(f'{final_file} exists.. skipping')
            return

        self.first_warp()

        cutline_file = workdir.joinpath('cutline.geojson')
        warped_file = workdir.joinpath('warped.tif')

        sheet_ibox = self.get_updated_sheet_ibox()
        cutline_crs_proj = 'EPSG:4326'

        self.create_cutline(sheet_ibox, cutline_file)

        img_quality_config = {
            'COMPRESS': 'DEFLATE',
            'PREDICTOR': '2',
            #'PHOTOMETRIC': 'YCBCR',
            #'JPEG_QUALITY': self.warp_jpeg_quality,
            'TILED': 'YES',
            'BIGTIFF': 'IF_SAFER',
        }
        crs_proj = self.get_crs_proj()
        warp_quality_options = ' '.join([ f'-co {k}={v}' for k,v in img_quality_config.items() ])
        #res = self.get_resolution()
        #size_options = f'-tr {res} {res}'
        size_options = ''
        reproj_options = f'{size_options} -r bilinear -t_srs "EPSG:3857" -s_srs "{crs_proj}"' 
        nodata_options = '-dstalpha'
        perf_options = '-multi -wo NUM_THREADS=ALL_CPUS --config GDAL_CACHEMAX 1024 -wm 1024' 
        cutline_options = f'-cutline {str(cutline_file)} -cutline_srs "{cutline_crs_proj}" -crop_to_cutline --config GDALWARP_IGNORE_BAD_CUTLINE YES -wo CUTLINE_ALL_TOUCHED=TRUE'
        warp_cmd = f'gdalwarp -overwrite {perf_options} {nodata_options} {reproj_options} {warp_quality_options} {cutline_options} {str(warped_file)} {str(final_file)}'
        self.run_external(warp_cmd)


    def get_crs_proj(self):
        self.process_map_file()

        mid_lon, mid_lat = get_mids(self.get_sheet_ibox())

        if self.projinfo is None or self.projinfo.get('parallels', None) is None:
            crs_proj = '+proj=stere +lat_0=90 +lat_ts=81.05 +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
            return crs_proj

        parallels = self.projinfo['parallels']
        parallel1 = parallels[0]
        parallel2 = parallels[1]
        parallel_mid = (parallel1 + parallel2) / 2
        if mid_lat < 0:
            parallel1 = -parallel1
            parallel2 = -parallel2
            parallel_mid = -parallel_mid

        c_factor = self.projinfo['convergence']
        crs_proj = f'+proj=lcc +lat_1={parallel1} +lat_2={parallel2} +lat_0={parallel_mid} +lon_0=0 +k_0={c_factor} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'

        return crs_proj

    def get_scale(self):
        return 500000


def get_sheetmap():
    with open('mapstor/data/sheet_map.json', 'r') as f:
        sheet_map = json.load(f)
    return sheet_map

def get_bad_sheet_ids():
    bad_sheets_file = Path('mapstor/bad_sheets.txt')
    if not bad_sheets_file.exists():
        return []
    with open(bad_sheets_file, 'r') as f:
        bad_sheet_ids = [ line.strip() for line in f.readlines() if line.strip() != '' ]
    return bad_sheet_ids

def process_files():
    
    data_dir = Path('mapstor/data/raw')
    
    from_list_file = os.environ.get('FROM_LIST', None)
    if from_list_file is not None:
        fnames = Path(from_list_file).read_text().split('\n')
        image_files = [ Path(f'{data_dir}/{f.strip()}') for f in fnames if f.strip() != '']
    else:
        # Find all jpg files
        print(f"Finding jpg files in {data_dir}")
        image_files = list(data_dir.glob("**/*.gif"))

    print(f"Found {len(image_files)} gif files")

    projinfo_map = json.loads(Path('pcl/data/proj_map.json').read_text())
    
    special_cases_file = Path(__file__).parent / 'mapstor'/ 'special_cases.json'

    special_cases = {}
    if special_cases_file.exists():
        special_cases = json.loads(special_cases_file.read_text())

    sheet_map = get_sheetmap()

    bad_sheet_ids = get_bad_sheet_ids()

    total = len(image_files)
    processed_count = 0
    failed_count = 0
    success_count = 0
    # Process each file
    for filepath in image_files:
        print(f'==========  Processed: {processed_count}/{total} Success: {success_count} Failed: {failed_count} processing {filepath.name} ==========')
        extra = special_cases.get(filepath.name, {})
        id = filepath.name.replace('.gif', '')
        if id in bad_sheet_ids:
            continue
        sheet_props = sheet_map[id]
        sheet_props['source_type'] = 'mapstor'
        projinfo = projinfo_map.get(id, None)

        subs = []
        if 'parts' not in extra:
            subs.append([id, extra])
        else:
            for i, part in enumerate(extra['parts']):
                subs.append([f'{id}-part{i}', part])


        for subid, subextra in subs:
            all_items = []
            all_items.append((subid, subextra))
            for inset in subextra.get('insets', []):
                inset_id = f"{subid}-inset{len(all_items) - 1}"
                all_items.append((inset_id, inset))
                if 'inset_pixel_cutlines' not in subextra:
                    subextra['inset_pixel_cutlines'] = []
                subextra['inset_pixel_cutlines'].extend(inset['pixel_cutlines'])

            for item_id, item_extra in all_items:
                processor = TPCMapstorProcessor(filepath, item_extra, [], sheet_props, projinfo, item_id)
                try:
                    processor.process()
                    success_count += 1
                except Exception as ex:
                    print(f'parsing {filepath} failed with exception: {ex}')
                    failed_count += 1
                    traceback.print_exc()
                    #raise
                    processor.prompt()
                processed_count += 1

    print(f"Processed {processed_count} images, failed_count {failed_count}, success_count {success_count}")


if __name__ == "__main__":
    import os
    os.environ['GDAL_PAM_ENABLED'] = 'NO'
    process_files()
 
