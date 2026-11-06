"""Driver: seed -> ICP -> (h1,h0) search -> integer polish."""
import json
import sys
import time

import numpy as np

import fitlib as F
import icp
from icp import Fit, DOC, O0


def seed(caps, o, G, d, h1, h0, lo=2465.0, hi=2550.0, step=0.4):
    t0s = np.arange(-400.0, 550.0, 8.0)
    T0, K = [], []
    for c in caps:
        hbar = float(c["alv"].sum()) / (c["an"] / 8.0)   # highs per loop
        Leff = np.arange(lo, hi, step)
        ks = Leff / (G - d * hbar)
        A = F.A_of(c, o, G, d)
        B = F.edges_of(c["bits"], h1, h0)
        v, t0, k, m = F.fit_tk_grid(A, B, c["alv"], t0s, ks)
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k)
        T0.append(t0)
        K.append(k)
    return np.array(T0), np.array(K)


def polish_all(fit, rounds=8, log=print):
    """Integer coordinate polish on the raw match count."""
    caps = fit.caps

    def refit_nuis():
        T, A = fit.times()
        for j, c in enumerate(caps):
            m = fit.cidx == j
            Aj = A[m]
            v, mm, t0, k = F.polish_tk(Aj, fit.Bs[j], fit.lv[m],
                                       fit.t0[j], fit.k[j], st=12.0, sk=2e-5)
            fit.t0[j], fit.k[j] = t0, k
        return fit.matches()

    best = refit_nuis()
    log(f"   polish seed m={best} ({100*best/fit.n:.3f}%)")
    for step in (4.0, 1.5, 0.5, 0.15, 0.05):
        for rnd in range(rounds):
            prev = best
            for s in range(1, 8):
                cur = fit.o[s]
                for z in cur + np.arange(-6, 7) * step:
                    fit.o[s] = z
                    m = fit.matches()
                    if m > best:
                        best, cur = m, z
                fit.o[s] = cur
            cur = fit.G
            for z in cur + np.arange(-6, 7) * step * 0.3:
                fit.G = z
                m = fit.matches()
                if m > best:
                    best, cur = m, z
            fit.G = cur
            cur = fit.d
            for z in cur + np.arange(-6, 7) * step * 0.6:
                fit.d = z
                m = fit.matches()
                if m > best:
                    best, cur = m, z
            fit.d = cur
            for name in ("h1", "h0"):
                cur = getattr(fit, name)
                bz = cur
                for z in cur + np.arange(-6, 7) * step:
                    setattr(fit, name, z)
                    fit.rebuild_edges()
                    m = fit.matches()
                    if m > best:
                        best, bz = m, z
                setattr(fit, name, bz)
                fit.rebuild_edges()
            best = refit_nuis()
            log(f"   polish s={step} r{rnd}: m={best} ({100*best/fit.n:.3f}%) "
                f"G={fit.G:.2f} d={fit.d:.2f} h1={fit.h1:.1f} h0={fit.h0:.1f} "
                f"o={np.round(fit.o,1).tolist()}")
            if best <= prev:
                break
    return best


def main():
    out = sys.argv[1]
    meta, caps = F.load()
    G0 = 2500.0
    o0 = list(DOC * G0 / 37.0)
    o0[0] = O0
    t = time.time()
    T0, K = seed(caps, o0, G0, 0.0, 750.0, 375.0)
    print(f"seed done [{time.time()-t:.0f}s]", flush=True)
    fit = Fit(caps, o0, G0, 0.0, 750.0, 375.0, T0, K)
    print(f"seed m={fit.matches()} ({100*fit.matches()/fit.n:.3f}%)", flush=True)

    for outer in range(4):
        icp.run_icp(fit, iters=25, log=lambda s: print(s, flush=True))
        # (h1,h0) grid
        best = fit.matches()
        for _ in range(3):
            improved = False
            for name, rng in (("h1", 8.0), ("h0", 8.0)):
                cur = getattr(fit, name)
                bz = cur
                for z in cur + np.arange(-8, 9) * rng / 4:
                    setattr(fit, name, z)
                    fit.rebuild_edges()
                    m = fit.matches()
                    if m > best:
                        best, bz, improved = m, z, True
                setattr(fit, name, bz)
                fit.rebuild_edges()
            if not improved:
                break
        print(f" outer{outer}: after h-search m={best} "
              f"({100*best/fit.n:.3f}%) h1={fit.h1:.2f} h0={fit.h0:.2f}",
              flush=True)

    best = polish_all(fit, log=lambda s: print(s, flush=True))
    print(f"FINAL active m={best} ({100*best/fit.n:.3f}%)", flush=True)
    json.dump(dict(o=fit.o.tolist(), G=fit.G, d=fit.d, h1=fit.h1, h0=fit.h0,
                   t0=fit.t0.tolist(), k=fit.k.tolist(),
                   keys=[c["key"] for c in caps], act=best / fit.n),
              open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
