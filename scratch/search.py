import os
import sys

# Search terms
search_terms = ['process_field_zones', 'gonen_kav_2', 'edigan', 'gadash_edigan']

print("Searching for terms:", search_terms)

for root, dirs, files in os.walk('.'):
    # skip virtual env and git folders
    if '.venv' in root or '.git' in root or '.idea' in root:
        continue
    for f in files:
        if f.endswith(('.py', '.ipynb', '.txt', '.md')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as src:
                    content = src.read()
                    for term in search_terms:
                        if term in content:
                            print(f'Match found for "{term}" in: {path}')
            except Exception as e:
                pass
