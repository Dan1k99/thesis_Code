import json

with open('pipeline.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

def print_function_def(cell_source, func_name):
    lines = cell_source.split('\n')
    start_idx = -1
    for idx, line in enumerate(lines):
        if f"def {func_name}" in line:
            start_idx = idx
            break
            
    if start_idx == -1:
        return
        
    func_lines = []
    indent_level = None
    for line in lines[start_idx:]:
        stripped = line.lstrip()
        if not stripped:
            func_lines.append(line)
            continue
        # Check indent
        current_indent = len(line) - len(stripped)
        if indent_level is None:
            # First line of function
            indent_level = current_indent
            func_lines.append(line)
        else:
            if current_indent <= indent_level and stripped.startswith('def '):
                # Another function definition at same or parent level
                break
            func_lines.append(line)
            
    print('\n'.join(func_lines))

print("=== CELL 19: get_valid_chips_for_field ===")
print_function_def(''.join(nb['cells'][19]['source']), 'get_valid_chips_for_field')
print("="*40)

print("=== CELL 54: get_valid_chips_for_field ===")
print_function_def(''.join(nb['cells'][54]['source']), 'get_valid_chips_for_field')
print("="*40)
