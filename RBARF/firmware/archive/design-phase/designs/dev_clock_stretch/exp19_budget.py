"""Consolidated numbers for the design doc.

(1) per-capture L from the recommended pipeline, spread, implied eps
(2) integer bit-origin k0 distribution and the trigger phase phi
(3) samples per bit window under the fitted grid
(4) sharpness of the coarse periodogram (L posterior width) -> soft output
(5) sensitivity: bit-index error at the END of the frame vs dL
"""
import numpy as np
from common import load_all, BIT_NS
from exp8_pipeline import A, BIAS_F, coarse, refine, sample_times, hdr_score, slice_bits

NB = 192
meta, caps = load_all()
LG = np.arange(2300.0, 2705.0, 2.0)
LGF = np.arange(2460.0, 2540.0, 0.05)

Ls, phis, k0s, spb, halfw = [], [], [], [], []
for cap in caps:
    Lc, J, prof = coarse(cap, LG)
    phi, L, res, k, umid, s0 = refine(cap, Lc)
    Ls.append(L); phis.append(phi)
    best = None
    for k0 in (-2, -1, 0, 1, 2):
        bits, conf = slice_bits(cap, phi, L, k0)
        sc = hdr_score(bits)
        if best is None or sc > best[0]:
            best = (sc, k0)
    k0s.append(best[1])
    t = sample_times(cap, phi, L)
    kk = np.floor(t / BIT_NS).astype(int)
    cnt = np.array([(kk == b).sum() for b in range(NB)])
    spb.append(cnt)
    # fine periodogram half-width at 0.99 of peak
    j = np.array([abs((np.sinc((umid*0+1)*0+1)*0+1).sum()) for _ in (0,)])  # placeholder

Ls = np.array(Ls); phis = np.array(phis); k0s = np.array(k0s)
spb = np.array(spb)
print(f"L: mean={Ls.mean():.3f} std={Ls.std():.3f} min={Ls.min():.2f} max={Ls.max():.2f}")
print(f"   implied eps spread = {(Ls.max()/Ls.min()-1)*100:.4f}% ; "
      f"eps vs 2500 nominal = {(2500/Ls.mean()-1)*100:+.4f}%")
print(f"phi: mean={phis.mean():.1f} std={phis.std():.1f} "
      f"min={phis.min():.1f} max={phis.max():.1f}")
print(f"k0 distribution: {dict(zip(*np.unique(k0s, return_counts=True)))}")
print(f"samples per bit window: mean={spb.mean():.3f} "
      f"hist={np.bincount(spb.ravel()).tolist()}")
print(f"  bits with <=2 samples: {(spb<=2).mean():.3%}; ==0: {(spb==0).mean():.4%}")

print("\n== coarse periodogram peak sharpness (real, capture 0) ==")
from exp8_pipeline import coarse as C
for cap in caps[:3]:
    Lc, J, prof = C(cap, LGF)
    pk = prof.max(); m = prof > 0.99 * pk
    idx = np.nonzero(m)[0]
    print(f"{cap['pattern']:8s} peak L={LGF[np.argmax(prof)]:.2f} J={pk:.4f} "
          f"width@0.99pk = {(LGF[idx[-1]]-LGF[idx[0]]):.2f} ns; "
          f"width@0.95pk = {(LGF[prof>0.95*pk][-1]-LGF[prof>0.95*pk][0]):.2f} ns")

print("\n== dL -> accumulated timing error / bit slip at end of frame ==")
U = 96.0
for dL in (0.1, 0.25, 0.5, 1.0, 2.0, 4.5, 6.5, 13.0):
    print(f"  dL={dL:5.2f} ns ({dL/2500*100:+.3f}%): end-of-frame shift "
          f"{U*dL:7.1f} ns = {U*dL/BIT_NS:.3f} bit")
