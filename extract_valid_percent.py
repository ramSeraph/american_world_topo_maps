
import csv
import os
import subprocess
from pathlib import Path

def get_valid_percent(file_path):
    """Extracts the STATISTICS_VALID_PERCENT from a GeoTIFF file."""
    try:
        result = subprocess.run(
            ['gdalinfo', '-stats', str(file_path)],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if 'STATISTICS_VALID_PERCENT' in line:
                return line.split('=')[1]
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return None

def main():
    """
    Main function to extract valid percentages and update the CSV.
    """
    gtiffs_dir = Path('export/kmzs/gtiffs')
    valid_csv_path = Path('valid.csv')

    existing_files = set()
    if valid_csv_path.exists():
        with open(valid_csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                if row:
                    existing_files.add(row[0])

    with open(valid_csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not existing_files:
            writer.writerow(['File', 'STATISTICS_VALID_PERCENT'])

        for file_path in gtiffs_dir.glob('*.tif'):
            if file_path.name not in existing_files:
                valid_percent = get_valid_percent(file_path)
                if valid_percent is not None:
                    writer.writerow([file_path.name, valid_percent])
                    print(f"Processed {file_path.name}")

if __name__ == '__main__':
    main()
