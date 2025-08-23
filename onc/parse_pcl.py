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

#from PIL import Image
#from pyproj import Transformer, CRS

#from topo_map_processor.processor import TopoMapProcessor

from parse_mapstor import ONCMapstorProcessor

def get_mids(polygon):
    """
    Calculate the center of a polygon defined by a list of (x, y) tuples.
    """

    lons = [point[0] for point in polygon]
    lats = [point[1] for point in polygon]
    max_lon = max(lons)
    min_lon = min(lons)
    mid_lon = (max_lon + min_lon) / 2

    max_lat = max(lats)
    min_lat = min(lats)
    mid_lat = (max_lat + min_lat) / 2

    return mid_lon, mid_lat

class ONCPCLProcessor(ONCMapstorProcessor):

    def __init__(self, filepath, extra, index_box, index_properties, projinfo=None, id_override=None):
        super().__init__(filepath, extra, index_box, index_properties, projinfo)
        self.corner_gcps = extra.get('corner_gcps', None)
        self.other_gcps = extra.get('other_gcps', None)
        self.id_override = id_override

    def prompt1(self):
        pass

    def get_id(self):
        if self.id_override is not None:
            return self.id_override

        return super().get_id()

    def get_gcps(self, pre_rotated=False):

        frm = []
        frm.extend(self.corner_gcps if self.corner_gcps is not None else [])
        frm.extend(self.other_gcps if self.other_gcps is not None else [])

        if not frm:
            raise ValueError("No GCPs provided")

        gcps = []
        for item in frm:
            gcps.append([(item['x'], item['y']),
                        (item['lon'], item['lat'])])
        return gcps

    def get_sheet_ibox(self):
        if self.cutline_override is not None:
            return self.cutline_override

        if self.corner_gcps is None or len(self.corner_gcps) < 4:
            raise ValueError("Not enough corner GCPs provided")
        # Assuming corner_gcps is a list of dictionaries with 'x', 'y', 'lon', 'lat' keys

        corners = self.corner_gcps
        cutline = [ (corner['lon'], corner['lat']) for corner in corners ]
        cutline = cutline + [cutline[0]]  # Close the polygon

        return cutline

    #def get_full_pixel_cutline(self, pre_rotated=False):
    #    return super(ONCMapstorProcessor, self).get_full_pixel_cutline(pre_rotated)

    def process_map_file(self):
        pass

    def rotate(self):
        pass

    def get_scale(self):
        return 1000000


    def get_corners(self, pre_rotated=False):
        if self.cutline_override is not None:
            gcps = self.get_gcps()
            transformer = self.get_transformer_from_gcps(gcps)
            corners = []
            for corner in self.cutline_override:
                x, y = transformer.rowcol(corner[0], corner[1])
                corners.append((x, y))
            return corners[:-1]

        if self.corner_gcps is not None:
            corners = self.corner_gcps
            corners = [(corner['x'], corner['y']) for corner in corners]
            return corners

        raise ValueError("No cutline override or corner GCPs provided")




def get_sheetmap():
    with open('pcl/data/sheet_map.json', 'r') as f:
        sheet_map = json.load(f)
    return sheet_map


def process_files():
    
    data_dir = Path('pcl/data/raw')
    
    from_list_file = os.environ.get('FROM_LIST', None)
    if from_list_file is not None:
        fnames = Path(from_list_file).read_text().split('\n')
        image_files = [ Path(f'{data_dir}/{f.strip()}') for f in fnames if f.strip() != '']
    else:
        # Find all jpg files
        print(f"Finding jpg files in {data_dir}")
        image_files = list(data_dir.glob("**/*.jpg"))

    print(f"Found {len(image_files)} jpg files")

    projinfo_map = json.loads(Path('pcl/data/proj_map.json').read_text())
    
    special_cases_file = Path(__file__).parent / 'pcl' / 'special_cases.json'

    special_cases = {}
    if special_cases_file.exists():
        special_cases = json.loads(special_cases_file.read_text())

    sheet_map = get_sheetmap()

    total = len(image_files)
    processed_count = 0
    failed_count = 0
    success_count = 0
    # Process each file
    for filepath in image_files:
        print(f'==========  Processed: {processed_count}/{total} Success: {success_count} Failed: {failed_count} processing {filepath.name} ==========')
        extra = special_cases.get(filepath.name, {})
        id = filepath.name.replace('.jpg', '')
        sheet_props = sheet_map[id]
        sheet_props['source_type'] = 'pcl'
        projinfo = projinfo_map.get(id, None)
        subs = []
        if 'parts' not in extra:
            subs.append([id, extra])
        else:
            for i, part in enumerate(extra['parts']):
                subs.append([f'{id}-part{i}', part])

        for subid, subextra in subs:
            processor = ONCPCLProcessor(filepath, subextra, [], sheet_props, projinfo, subid)

            try:
                processor.process()
                success_count += 1
            except Exception as ex:
                print(f'parsing {filepath} failed with exception: {ex}')
                failed_count += 1
                traceback.print_exc()
                raise
                processor.prompt()
            processed_count += 1

    print(f"Processed {processed_count} images, failed_count {failed_count}, success_count {success_count}")


if __name__ == "__main__":
    import os
    os.environ['GDAL_PAM_ENABLED'] = 'NO'
    process_files()
 
