import json

with open('pipeline.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def get_valid_chips_for_field' in source:
            print(f"Cell {i} has the term 'def get_valid_chips_for_field'")
            print("First 15 lines:")
            lines = source.split('\n')
            for line in lines[:15]:
                print("  ", line)
            print("="*30)
