"""Blind (data-independent) clock estimator: rising-edge periodogram.

Every WS2812 rising edge sits at exactly k*1250 ns. An observed 0->1
transition between samples n and n+1 brackets one such edge. Under the
sampler model t(i,s) = (i + a[s]) * L, scan L and evaluate

    Z(L) = SUM_j sinc(gap_j / T) * exp(2*pi*i * tmid_j / T),  T = 1250 ns

|Z| peaks at the true loop period; arg(Z) gives the bit-grid phase.
No knowledge of the payload is used.  Ground truth is only used at the
end to report the error.
"""
import numpy as np
from common import load_all, BIT_NS

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0   # doc model
A_FIT = np.array([1.0, 5.0, 8.2, 14.56, 17.6, 21.0, 26.76, 32.0]) / 40.0


def rise_brackets(cap, a):
    lev = cap["lev"]
    d = np.diff(lev.astype(int))
    idx = np.nonzero(d > 0)[0]
    u = cap["it"] + a[cap["slot"]]        # sample time in loop units
    return u[idx], u[idx + 1]


def periodogram(u0, u1, Ls, T=BIT_NS):
    """|Z| and arg(Z) for each candidate loop period L."""
    mag = np.empty(len(Ls)); ph = np.empty(len(Ls))
    for k, L in enumerate(Ls):
        t0, t1 = u0 * L, u1 * L
        g = t1 - t0
        w = np.sinc(g / T)                # np.sinc(x)=sin(pi x)/(pi x)
        z = (w * np.exp(2j * np.pi * (0.5 * (t0 + t1)) / T)).sum()
        mag[k] = abs(z); ph[k] = np.angle(z)
    return mag, ph


def estimate(cap, a, Lgrid):
    u0, u1 = rise_brackets(cap, a)
    mag, ph = periodogram(u0, u1, Lgrid)
    k = int(np.argmax(mag))
    # parabolic interpolation on the peak
    if 0 < k < len(Lgrid) - 1:
        y0, y1, y2 = mag[k-1], mag[k], mag[k+1]
        d = 0.5 * (y0 - y2) / (y0 - 2*y1 + y2 + 1e-12)
        Lhat = Lgrid[k] + d * (Lgrid[1] - Lgrid[0])
    else:
        Lhat = Lgrid[k]
    return Lhat, mag, ph, k, len(u0)


if __name__ == "__main__":
    meta, caps = load_all()
    import json
    ref = {(c["pattern"], c["rep"]): c for c in
           json.load(open("fit_joint.json"))["caps"]}

    Lgrid = np.arange(2300.0, 2700.0, 0.10)
    print(f"{'pattern':11s} {'rep':>3s} {'Lhat_doc':>9s} {'Lhat_fit':>9s} "
          f"{'Ljoint':>9s} {'nrise':>5s} {'peak/2nd':>9s}")
    errs = []
    for cap in caps:
        Ld, magd, *_ , nr = estimate(cap, A, Lgrid)
        Lf, magf, phf, kf, nr = estimate(cap, A_FIT, Lgrid)
        # sidelobe ratio: best magnitude outside +-15 ns of the peak
        m = magf.copy()
        far = np.abs(Lgrid - Lf) > 15.0
        ratio = magf[kf] / m[far].max()
        Lj = ref[(cap["pattern"], cap["rep"])]["L"]
        errs.append(Lf - Lj)
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {Ld:9.2f} {Lf:9.2f} "
              f"{Lj:9.2f} {nr:5d} {ratio:9.3f}")
    errs = np.array(errs)
    print(f"\nLhat_fit - L_joint: mean={errs.mean():+.2f} std={errs.std():.2f} "
          f"max|.|={np.abs(errs).max():.2f} ns  "
          f"(={np.abs(errs).max()/2500*100:.3f}% of loop)")
