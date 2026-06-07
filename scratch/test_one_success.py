import sys
import os
sys.path.append(os.getcwd())
import time
import build_pixel_datasets

start = time.time()
print("Processing Eden_gimel.csv...")
result = build_pixel_datasets.process_single_field("Boundary_Fields_Baseline_2011 — Eden_gimel.csv")
print("Result:", result)
print(f"Time taken: {time.time() - start:.2f} seconds")
