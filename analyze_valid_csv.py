#!/usr/bin/env python3
import csv
from collections import defaultdict

def analyze_valid_csv():
    intervals = defaultdict(int)
    
    with open('valid.csv', 'r') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            percent = float(row['STATISTICS_VALID_PERCENT'])
            # check if the percent is a proper integer use some epsilon to avoid floating point issues

            interval = int(percent)
            intervals[interval] += 1
    
    print("1% Interval Distribution:")
    print("Interval\tCount")
    print("-" * 20)
    
    for interval in sorted(intervals.keys()):
        if intervals[interval] > 0:
            print(f"{interval}-{interval+1}%\t{intervals[interval]}")

if __name__ == "__main__":
    analyze_valid_csv()
