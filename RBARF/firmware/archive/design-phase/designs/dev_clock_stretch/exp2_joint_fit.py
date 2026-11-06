"""Joint fit: global slot fractions a[0..7] + per-capture (phi, L).

Model:  t(i,s) = phi + (i + a[s]) * L      (L = loop duration in ns)
Objective: number of samples whose ideal-waveform level matches the
observed level (ground truth used -- analysis only).

Purpose: get an *unbiased* per-capture clock estimate (L) so we can see
how much of the apparent 1.14% spread in exp1 was slot-model error.
"""
import json
import numpy as np
from common import load_all, wave

A0 = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0


def score_cap(cap, phi, L, a):
    t = phi + (cap["it"] + a[cap["slot"]]) * L
    return int((wave(cap["bits"], t) == cap["lev"]).sum())


def refine_phi_L(cap, phi, L, a, dphi, dL, nphi=9, nL=9):
    best = (score_cap(cap, phi, L, a), phi, L)
    for p in phi + np.linspace(-dphi, dphi, nphi):
        for l in L + np.linspace(-dL, dL, nL):
            s = score_cap(cap, p, l, a)
            if s > best[0]:
                best = (s, p, l)
    return best


def main():
    meta, caps = load_all()
    a = A0.copy()
    st = [dict(phi=200.0, L=2500.0) for _ in caps]
    # coarse acquisition per capture
    for c, s in zip(caps, st):
        best = (-1, 0, 0)
        for L in np.arange(2480, 2540, 2.0):
            for phi in np.arange(-600, 600, 40.0):
                v = score_cap(c, phi, L, a)
                if v > best[0]:
                    best = (v, phi, L)
        s["phi"], s["L"] = best[1], best[2]

    for it in range(8):
        dphi, dL = (60.0, 1.5) if it < 3 else (12.0, 0.25)
        tot = 0
        for c, s in zip(caps, st):
            v, s["phi"], s["L"] = refine_phi_L(c, s["phi"], s["L"], a, dphi, dL)
            tot += v
        # global slot fractions (slot 0 fixed -> absorbed by phi)
        for j in range(1, 8):
            step = 0.02 if it < 3 else 0.004
            cands = a[j] + np.linspace(-step, step, 9)
            bestv, bestc = -1, a[j]
            for cand in cands:
                aa = a.copy(); aa[j] = cand
                v = sum(score_cap(c, s["phi"], s["L"], aa) for c, s in zip(caps, st))
                if v > bestv:
                    bestv, bestc = v, cand
            a[j] = bestc
        print(f"iter {it}: total={tot} ({tot/(54*5117):.4%}) "
              f"a={np.round(a*40, 3).tolist()}")

    Ls = np.array([s["L"] for s in st])
    print(f"\nslot cycle positions (x40): {np.round(a*40,3).tolist()}")
    print(f"inter-slot gaps (cy): "
          f"{np.round(np.diff(np.append(a*40, 40+a[0]*40)),3).tolist()}")
    print(f"\nL: mean={Ls.mean():.2f} std={Ls.std():.2f} min={Ls.min():.2f} "
          f"max={Ls.max():.2f} spread={(Ls.max()/Ls.min()-1)*100:.3f}%")
    for c, s in zip(caps, st):
        v = score_cap(c, s["phi"], s["L"], a)
        print(f"{c['pattern']:11s} {c['rep']} L={s['L']:8.2f} "
              f"eps={(2500.0/s['L']-1)*100:+7.3f}% phi={s['phi']:7.1f} "
              f"match={v/5117:.4%}")
    json.dump(dict(a=a.tolist(),
                   caps=[dict(pattern=c["pattern"], rep=c["rep"],
                              phi=s["phi"], L=s["L"]) for c, s in zip(caps, st)]),
              open("fit_joint.json", "w"), indent=1)


if __name__ == "__main__":
    main()
