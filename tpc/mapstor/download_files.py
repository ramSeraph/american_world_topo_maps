# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "remotezip",
# ]
# ///

import json
import remotezip
from pathlib import Path

def replace_fname(content, fname, replacement):
    txt = content.decode('cp1251')
    txt = txt.replace(fname, replacement)
    return txt.encode('cp1251')


def main():
    data = json.loads(Path('data/sheet_map.json').read_text())
    for k, item in data.items():
        url = item.get('url')
        gif_fname = item.get('filename')
        map_fname = gif_fname.replace('.gif', '.map')
        try:
            with remotezip.RemoteZip(url) as zip_file:
                # extract just fname file from archive
                for fname in [gif_fname, map_fname]:
                    fname_full = f"maps/{fname}"
                    out_fname = f'{k}.gif' if fname == gif_fname else f'{k}.map'
                    output_path = Path('data/raw') / out_fname
                    if output_path.exists():
                        print(f"Skipping {fname} {url}, already exists at {output_path}")
                        continue
                    if fname_full in zip_file.namelist():
                        with zip_file.open(fname_full) as file:
                            content = file.read()
                            # Save the content to a local file
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            if fname == map_fname:
                                content = replace_fname(content, gif_fname, f'{k}.gif')
                            output_path.write_bytes(content)
                            print(f"Downloaded {fname} from {url} to {output_path}")
                    else:
                        print(f"{fname} not found in {url}")
        except Exception as e:
            print(f"Error processing {fname} {url}: {e}")


if __name__ == "__main__":
    main()
