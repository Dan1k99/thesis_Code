import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

for item in os.listdir('.'):
    if os.path.isdir(item):
        if item in ['.git', '.venv', '.idea']:
            continue
        try:
            files = []
            for root, dirs, f_list in os.walk(item):
                for f in f_list:
                    files.append(os.path.join(root, f))
            print(f"Directory: {item} | Total files: {len(files)} | Example files: {files[:5]}")
        except Exception as e:
            print(f"Error reading {item}: {e}")
