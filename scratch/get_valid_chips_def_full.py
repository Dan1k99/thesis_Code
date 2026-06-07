import json

with open('pipeline.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def get_valid_chips_for_field' in source:
            print(f"=== CELL {i} ===")
            print(source)
            print("="*20)
