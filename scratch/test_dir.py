import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Direct check for 'איתירועי':")
path1 = 'איתירועי'
print(f"Path '{path1}' exists:", os.path.exists(path1))

# Try looking at all names in current folder using different encodings
print("\nTraversing current directory to find any non-ASCII folders:")
for x in os.listdir('.'):
    if any(ord(c) > 127 for c in x):
        print(f"Found non-ASCII: {repr(x)} (bytes: {x.encode('utf-8')})")
        print(f"Exists: {os.path.exists(x)}")
        if os.path.isdir(x):
            print(f"Contents of {x}:", os.listdir(x))
