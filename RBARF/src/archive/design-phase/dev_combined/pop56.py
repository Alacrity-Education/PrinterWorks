#!/usr/bin/env python3
"""Measure the (5,6)-bracket ambiguous population and test whether a local
rise-interval phase correction separates truth=0 from truth=1."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset, linearize  # noqa: E402
import combined as C  # noqa: E402


def frame_bits(payload_hex):
    fr = C.HDR + bytes.fromhex(payload_hex) + C.TRL
    return C._bits_of(fr)


def local_delta(seg, j, wbits):
    """Greedy intersection of rise-offset intervals around pulse j."""
    k0 = seg[j]["k0"]
    lo, hi = seg[j]["rlo"], seg[j]["rhi"]
    order = sorted(range(len(seg)), key=lambda m: abs(seg[m]["k0"] - k0))
    for m in order:
        if m == j or abs(seg[m]["k0"] - k0) > wbits:
            continue
        nlo = max(lo, seg[m]["rlo"])
        nhi = min(hi, seg[m]["rhi"])
        if nlo <= nhi:
            lo, hi = nlo, nhi
    return (lo + hi) / 2.0, hi - lo


def main():
    meta, caps = load_dataset()
    caps = [c for c in caps if c["rep"] in (0, 1)]
    model = C.MODELS[0]
    rows = []
    for c in caps:
        samples = linearize(c["capture"])
        truth = frame_bits(c["payload"])
        pulses = C._model_clock_pulses(samples, model)
        # keep raw rise brackets alongside
        cands = C._hough_candidates(pulses)
        kappa, tau, hits, resid = cands[0]
        # segment with rise info
        mapped = []
        for (ra, rb, fa, fb, sfa, sfb, nh) in pulses:
            rm = kappa * (ra + rb) * 0.5 + tau
            if rm >= C.NB * C.BIT + C.TAIL_NS:
                continue
            mapped.append([rm, kappa * ra + tau, kappa * rb + tau,
                           kappa * fa + tau, kappa * fb + tau, sfa, sfb, nh])
        n = [0]
        for j in range(1, len(mapped)):
            d = int(round((mapped[j][0] - mapped[j - 1][0]) / C.BIT))
            n.append(n[-1] + max(0, d))
        seg = []
        for j, mp in enumerate(mapped):
            if n[j] >= C.NB or (seg and n[j] == seg[-1]["k0"]):
                continue
            seg.append(dict(k0=n[j], rlo=mp[1] - n[j] * C.BIT,
                            rhi=mp[2] - n[j] * C.BIT,
                            u=mp[3] - n[j] * C.BIT, v=mp[4] - n[j] * C.BIT,
                            sfa=mp[5], sfb=mp[6], nh=mp[7]))
        for j, p in enumerate(seg):
            k1 = seg[j + 1]["k0"] if j + 1 < len(seg) else C.NB
            L = k1 - p["k0"]
            if L != 1 or p["sfa"] != 5 or p["sfb"] != 6:
                continue
            if not (330 <= p["u"] <= 420):
                continue
            t = truth[p["k0"]]
            d4, w4 = local_delta(seg, j, 4)
            d8, w8 = local_delta(seg, j, 8)
            rows.append((c["pattern"] + "_" + str(c["rep"]), p["k0"], t,
                         p["u"], p["v"], (p["rlo"] + p["rhi"]) / 2, d4, w4, d8, w8))
    print(f"{'capture':12s} {'bit':>4s} T {'u':>7s} {'v':>7s} {'rmid':>7s} "
          f"{'d4':>7s} {'w4':>5s} {'u-d4':>7s} {'d8':>7s} {'u-d8':>7s}")
    for r in rows:
        print(f"{r[0]:12s} {r[1]:4d} {r[2]} {r[3]:7.1f} {r[4]:7.1f} {r[5]:7.1f} "
              f"{r[6]:7.1f} {r[7]:5.0f} {r[3]-r[6]:7.1f} {r[8]:7.1f} {r[3]-r[8]:7.1f}")
    # separability summary
    for name, idx in (("raw u", 3), ):
        u0 = sorted(r[idx] for r in rows if r[2] == 0)
        u1 = sorted(r[idx] for r in rows if r[2] == 1)
        print(f"\n{name}: n0={len(u0)} n1={len(u1)}")
        if u0 and u1:
            print(f"  truth0: {u0[0]:.0f}..{u0[-1]:.0f}  truth1: {u1[0]:.0f}..{u1[-1]:.0f}")
    c0 = sorted(r[3] - r[6] for r in rows if r[2] == 0)
    c1 = sorted(r[3] - r[6] for r in rows if r[2] == 1)
    if c0 and c1:
        print(f"corrected u-d4: truth0 {c0[0]:.0f}..{c0[-1]:.0f}  truth1 {c1[0]:.0f}..{c1[-1]:.0f}")
    c0 = sorted(r[3] - r[8] for r in rows if r[2] == 0)
    c1 = sorted(r[3] - r[8] for r in rows if r[2] == 1)
    if c0 and c1:
        print(f"corrected u-d8: truth0 {c0[0]:.0f}..{c0[-1]:.0f}  truth1 {c1[0]:.0f}..{c1[-1]:.0f}")


if __name__ == "__main__":
    main()
