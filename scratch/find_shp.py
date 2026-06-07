import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Searching for any file with .shp extension:")
count = 0
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.lower().endswith('.shp'):
            print(f"Found: {os.path.join(root, f)}")
            count += 1

print(f"Total .shp files found: {count}")
