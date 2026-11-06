"""(a) Coarse scale from the frame span anchor; (b) periodogram alias map.

Span anchor: capture is edge-triggered so the first rising edge is at
t=0 (just before sample (0,0)).  The frame's last falling edge (end of
trailer 0xFF) is at 191*1250+700 = 239450 ns.  The last 1->0 transition
in the capture brackets it -> a coarse L with accuracy set by the
bracket width alone (no data knowledge needed beyond the frame length).
"""
import json
import numpy as np
from common import load_all, BIT_NS
from exp3_periodogram import A, A_FIT, rise_brackets, periodogram

T_LAST_FALL = 191 * BIT_NS + 700.0        # 239450 ns
NBITS = 192


def span_estimate(cap, a):
    u = cap["it"] + a[cap["slot"]]
    lev = cap["lev"]
    hi = np.nonzero(lev == 1)[0]
    n = hi[-1]                                  # last high sample
    u_lo, u_hi = u[n], (u[n + 1] if n + 1 < len(u) else u[n] + 0.2)
    umid = 0.5 * (u_lo + u_hi)
    L = T_LAST_FALL / umid
    Lmin = T_LAST_FALL / u_hi
    Lmax = T_LAST_FALL / u_lo
    return L, Lmin, Lmax, umid


if __name__ == "__main__":
    meta, caps = load_all()
    ref = {(c["pattern"], c["rep"]): c["L"] for c in
           json.load(open("fit_joint.json"))["caps"]}
    Lgrid = np.arange(2300.0, 2700.0, 0.05)

    print("== span anchor ==")
    errs, halfw = [], []
    for cap in caps:
        L, Lmin, Lmax, umid = span_estimate(cap, A)
        Lj = ref[(cap["pattern"], cap["rep"])]
        errs.append(L - Lj); halfw.append(0.5 * (Lmax - Lmin))
        print(f"{cap['pattern']:11s} {cap['rep']} Lspan={L:8.2f} "
              f"[{Lmin:8.2f},{Lmax:8.2f}] hw={0.5*(Lmax-Lmin):5.2f} "
              f"Ljoint={Lj:8.2f} d={L-Lj:+6.2f}")
    errs = np.array(errs); halfw = np.array(halfw)
    print(f"span err: mean={errs.mean():+.2f} std={errs.std():.2f} "
          f"max|.|={np.abs(errs).max():.2f}  bracket halfwidth mean={halfw.mean():.2f}")

    print("\n== periodogram alias structure (top 5 peaks, A=doc) ==")
    for cap in caps[:54:3]:
        u0, u1 = rise_brackets(cap, A)
        mag, ph = periodogram(u0, u1, Lgrid)
        order = np.argsort(mag)[::-1]
        picked = []
        for k in order:
            if all(abs(Lgrid[k] - p) > 3.0 for p, _ in picked):
                picked.append((Lgrid[k], mag[k]))
            if len(picked) == 5:
                break
        Lj = ref[(cap["pattern"], cap["rep"])]
        s = "  ".join(f"{p:7.1f}({m/picked[0][1]:.2f})" for p, m in picked)
        print(f"{cap['pattern']:11s} {cap['rep']} Ljoint={Lj:7.1f} | {s}")
