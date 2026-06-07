import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Unfiltered recursive file list of withPoly_2025:")
for root, dirs, files in os.walk('withPoly_2025'):
    for f in files:
        # Ignore common sidecar files like .dbf, .shx, .prj, .cpg, .sbx, .sbn
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.dbf', '.shx', '.prj', '.cpg', '.sbx', '.sbn', '.xml']:
            continue
        print(f"  {os.path.join(root, f)}")
