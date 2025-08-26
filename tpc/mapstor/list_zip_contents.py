# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "remotezip",
# ]
# ///

import sys
import csv
import remotezip

def get_zip_file_list(url):
    """
    Returns a list of files in a remote zip file without downloading the whole file.
    """
    try:
        with remotezip.RemoteZip(url) as zip:
            return [name for name in zip.namelist()]
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

def main():
    if len(sys.argv) != 3:
        print("Usage: python list_zip_contents.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, 'r') as f_in, open(output_file, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["url", "filename"])

        for url in f_in:
            url = url.strip()
            if not url:
                continue

            print(f"Processing {url}...")
            files = get_zip_file_list(url)
            for file in files:
                writer.writerow([url, file])

    print(f"CSV file '{output_file}' created successfully.")

if __name__ == "__main__":
    main()

