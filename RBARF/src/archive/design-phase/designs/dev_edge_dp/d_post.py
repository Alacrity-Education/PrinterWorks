"""Reliability of edge_dp's per-bit posterior LLRs on the 54 real captures."""
import time
import numpy as np
import dp2, bcjr

meta, caps = dp2.CM.load()
WES = [32.0, 24.0, 28.0, 18.0, 12.0, 38.0, 26.0, 46.0]
CFG = dict(kgrid=tuple(np.arange(-0.001, 0.0071, 0.0005)), dlo=-900.0,
           dhi=900.0, d0sig=1000.0, we=25.0, floor=0.01, dstep=12.5,
           vpen=1.2, vmax=25.0, vstep=6.25, wes=WES, sr=40.0, dr=-28.0)
L=[]; T=[]
t0=time.time()
for c in caps:
    A = dp2.A_of(c)
    llr, lz = bcjr.run_capture_soft(c, A, **CFG)
    L.append(llr[32:160]); T.append(np.array(c["bits"])[32:160])
L=np.concatenate(L); T=np.concatenate(T)
hard=(L>0).astype(int)
print(f"MAP-bit error {int((hard!=T).sum())}/{len(T)} = {(hard!=T).mean():.5f} ({time.time()-t0:.0f}s)")
print("reliability of |LLR|:")
edges=[0,0.5,1,2,4,8,16,1e9]
for a,b in zip(edges[:-1],edges[1:]):
    m=(np.abs(L)>=a)&(np.abs(L)<b)
    if m.sum(): print(f"  {a:5.1f}<=|LLR|<{b:<6.1f} n={int(m.sum()):5d} err={(hard[m]!=T[m]).mean():.4f}")
for th in (1,2,4,8):
    m=np.abs(L)>=th
    print(f"  |LLR|>={th}: coverage {m.mean():.3f} err {(hard[m]!=T[m]).mean():.5f}")
np.save("post_llr.npy", L); np.save("post_true.npy", T)
