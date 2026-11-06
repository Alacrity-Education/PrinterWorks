"""(a) fix the eps=-8% grid-truncation artefact of exp23;
   (b) real-data precision of the censored estimator vs the QUALITY of the
       slot-fraction calibration a[]  (doc a, exp18-fitted a, and a
       coarse per-slot search that the calibration effort would supply)."""
import sys
import numpy as np
from common import load_all, BIT_NS, REC
sys.path.insert(0, str(REC))
from synth import synth_capture                      # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                        # noqa: E402
from exp9_envelope import pack, truth_L
from exp23_censored import acquire, polish, total

A_DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
A_FIT18 = np.array([0.0, 206.0, 500.0, 832.0, 1050.0, 1248.0, 1609.0, 2005.5]) / 2498.0
LGRID_W = np.arange(2280., 2740., 2.0)
PGRID = np.arange(-100., 400., 50.)

print("== eps=-0.08 with the grid widened to 2280..2740 ==")
err = []
for name, pay in PATTERNS.items():
    for r in range(3):
        cap = pack(synth_capture(pay, eps=-0.08, phase_ns=(r*83.)%250))
        v, phi, L = acquire(cap, A_DOC, LGRID_W, PGRID)
        phi, L, v = polish(cap, A_DOC, phi, L)
        err.append(abs(L - truth_L(-0.08)))
err = np.array(err)
print(f"  med={np.median(err):.3f} max={err.max():.3f} fail>4.5ns={(err>4.5).sum()}/54")

print("\n== real data: censored estimator vs slot-calibration quality ==")
meta, caps = load_all()
for tag, a in (("doc [1,5,9,13,17,21,27,32]/40", A_DOC),
               ("exp18-fitted offsets/2498", A_FIT18)):
    Ls = []
    for cap in caps:
        v, phi, L = acquire(cap, a, LGRID_W, PGRID)
        phi, L, v = polish(cap, a, phi, L)
        Ls.append(L)
    Ls = np.array(Ls)
    print(f"  {tag:32s}: L mean={Ls.mean():8.2f} std={Ls.std():5.2f} "
          f"min={Ls.min():8.2f} max={Ls.max():8.2f}")
