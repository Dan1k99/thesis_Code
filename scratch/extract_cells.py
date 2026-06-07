import json

with open('pipeline.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cells containing 'build_long_format_datasets' or cell indices around 18-20
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'extract_features_at_point' in source or 'build_long_format_datasets' in source:
            print(f"=== CELL {i} ===")
            print(source)
            print("="*20)
