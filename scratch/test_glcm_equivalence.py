import numpy as np
from skimage.feature import graycomatrix

W = np.random.randint(0, 256, (15, 15), dtype=np.uint8)
angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]

# 1. Standard SKImage GLCM
glcm = graycomatrix(W, [1], angles, symmetric=True, normed=True)
i_idx, j_idx = np.ogrid[:256, :256]
GLCM_HOMO_WEIGHTS = 1.0 / (1.0 + (i_idx - j_idx) ** 2)
GLCM_HOMO_WEIGHTS = GLCM_HOMO_WEIGHTS[:, :, np.newaxis, np.newaxis]

homo_sk = np.mean(np.sum(glcm * GLCM_HOMO_WEIGHTS, axis=(0, 1)))
asm_sk = np.mean(np.sum(glcm ** 2, axis=(0, 1)))

glcm_avg = np.mean(glcm, axis=3)[:, :, 0]
entropy_sk = -np.sum(glcm_avg[glcm_avg > 0] * np.log2(glcm_avg[glcm_avg > 0]))

# 2. Optimized np.bincount GLCM
h_A, h_B = W[:, :-1].ravel(), W[:, 1:].ravel()
v_A, v_B = W[:-1, :].ravel(), W[1:, :].ravel()
d1_A, d1_B = W[:-1, :-1].ravel(), W[1:, 1:].ravel()
d2_A, d2_B = W[:-1, 1:].ravel(), W[1:, :-1].ravel()

# For homogeneity, ASM, and average GLCM, we compute per direction
weights_flat = (1.0 / (1.0 + (i_idx - j_idx) ** 2)).ravel()

p_dirs = []
homos = []
asms = []
for A_dir, B_dir in [(h_A, h_B), (d1_A, d1_B), (v_A, v_B), (d2_A, d2_B)]:
    pairs_dir = A_dir.astype(np.int32) * 256 + B_dir.astype(np.int32)
    sym_pairs_dir = B_dir.astype(np.int32) * 256 + A_dir.astype(np.int32)
    all_pairs_dir = np.concatenate([pairs_dir, sym_pairs_dir])
    
    counts_dir = np.bincount(all_pairs_dir, minlength=256*256)
    p_dir = counts_dir / len(all_pairs_dir)
    
    p_dirs.append(p_dir)
    homos.append(np.sum(p_dir * weights_flat))
    asms.append(np.sum(p_dir ** 2))

homo_opt = np.mean(homos)
asm_opt = np.mean(asms)
p_avg = np.mean(p_dirs, axis=0)

p_avg_nz = p_avg[p_avg > 0]
entropy_opt = -np.sum(p_avg_nz * np.log2(p_avg_nz))

print("Homogeneity - SK:", homo_sk, "Opt:", homo_opt, "Diff:", abs(homo_sk - homo_opt))
print("ASM - SK:", asm_sk, "Opt:", asm_opt, "Diff:", abs(asm_sk - asm_opt))
print("Entropy - SK:", entropy_sk, "Opt:", entropy_opt, "Diff:", abs(entropy_sk - entropy_opt))
assert np.allclose(homo_sk, homo_opt)
assert np.allclose(asm_sk, asm_opt)
assert np.allclose(entropy_sk, entropy_opt)
print("All match perfectly!")
