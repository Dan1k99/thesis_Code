import shutil
import os

brain_dir = r"C:\Users\dani9\.gemini\antigravity\brain\61b2ff0e-ccb4-4d6e-aa38-2391cb5a6d61"
os.makedirs(brain_dir, exist_ok=True)

# 1. Historical example
# EHI tet 2012 has special characters in the saved name. We can find the filename using glob
import glob
hist_pattern = os.path.join("buffer_STD", "*ehi_tet*")
hist_matches = glob.glob(hist_pattern)
if hist_matches:
    src_hist = hist_matches[0]
    dst_hist = os.path.join(brain_dir, "historical_example.png")
    shutil.copy2(src_hist, dst_hist)
    print(f"Copied historical: {src_hist} -> {dst_hist}")

# 2. 2025 example
src_2025 = os.path.join("buffer_STD_2025", "broomrape_sampling_gonen_2025-06-30_buffer_std.png")
if os.path.exists(src_2025):
    dst_2025 = os.path.join(brain_dir, "2025_example.png")
    shutil.copy2(src_2025, dst_2025)
    print(f"Copied 2025: {src_2025} -> {dst_2025}")
