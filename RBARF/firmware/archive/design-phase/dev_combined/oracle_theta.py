#!/usr/bin/env python3
"""Ceiling analysis: per capture-family, compare
   (a) current label-only split,
   (b) semi-supervised split (labels hard + unlabeled 2-cluster gap),
   (c) ORACLE split (fit on truth),
each measured by residual misclassified last-bits, over the train captures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset, linearize  # noqa: E402
import combined as C  # noqa: E402


def frame_bits(payload_hex):
    fr = C.HDR + bytes.fromhex(payload_hex) + C.TRL
    return C._bits_of(fr)


def truth_a(truth, k0, k1):
    """leading-ones count of truth[k0:k1]"""
    a = 0
    for t in range(k0, k1):
        if truth[t] == 1:
            a += 1
        else:
            break
    return a


def split_errs(labs, th):
    return sum(1 for x, c in labs if (x > th) != (c == 1))


def best_split(labs):
    if not labs:
        return 0.0, 0
    pts = sorted(set(x for x, _ in labs))
    cands = [pts[0] - 20, pts[-1] + 20]
    for i in range(len(pts) - 1):
        cands.append((pts[i] + pts[i + 1]) / 2)
    best = None
    for th in cands:
        e = split_errs(labs, th)
        marg = min(abs(x - th) for x, _ in labs)
        if best is None or (e, -marg) < best[0]:
            best = ((e, -marg), th)
    return best[1], best[0][0]


def main():
    meta, caps = load_dataset()
    caps = [c for c in caps if c["rep"] in (0, 1)]
    model = C.MODELS[0]
    tot_cur = tot_orc = tot_all = 0
    percap = {}
    for c in caps:
        name = f"{c['pattern']}_{c['rep']}"
        samples = linearize(c["capture"])
        truth = frame_bits(c["payload"])
        pulses = C._model_clock_pulses(samples, model)
        kappa, tau, hits, resid = C._hough_candidates(pulses)[0]
        seg, slip0 = C._segment(pulses, kappa, tau)
        # all-pulse x with truth class, per family
        fam_pts = {}     # fam -> list of (x, truth_cls, is_marker)
        h0p, h1p = model["H0"], model["H1"]
        for j, p in enumerate(seg):
            k0, k1 = p["k0"], p["k1"]
            if k1 > C.NB:
                continue
            at = truth_a(truth, k0, min(k1, C.NB))
            li = C._label_interval(p, at, h0p, h1p)
            if li is None:
                continue
            cls, lo, hi = li
            marker = all(C.KNOWN[t] >= 0 for t in range(k0, k1))
            fam_pts.setdefault((p["sfa"], p["sfb"]), []).append(
                (lo, cls, marker))
        cap_cur = cap_orc = cap_n = 0
        for fam, pts in fam_pts.items():
            labs_all = [(x, c) for x, c, m in pts]
            labs_mark = [(x, c) for x, c, m in pts if m]
            # oracle split on everything
            th_o, e_o = best_split(labs_all)
            # current estimator: marker-label split around theta0
            g = sorted(p["v"] - p["u"] for p in seg
                       if (p["sfa"], p["sfb"]) == fam)
            gap = g[len(g) // 2]
            import math
            wa = math.hypot(C.WE[fam[0]], C.TB_NS)
            wb = math.hypot(C.WE[fam[1]], C.TB_NS)
            # crude global h estimate: priors (this is only a comparison)
            theta0 = (wb * h0p + wa * (h1p - gap)) / (wa + wb)
            th_c = C._fit_split(labs_mark, theta0)
            e_c = split_errs(labs_all, th_c)
            cap_cur += e_c
            cap_orc += e_o
            cap_n += len(pts)
        tot_cur += cap_cur
        tot_orc += cap_orc
        tot_all += cap_n
        percap[name] = (cap_cur, cap_orc, cap_n)
        if cap_cur or cap_orc:
            print(f"{name:14s} label-split errs={cap_cur:2d}  "
                  f"ORACLE errs={cap_orc:2d}  (pulses={cap_n})")
    print(f"\nTOTAL: label-split {tot_cur}, oracle {tot_orc}, "
          f"pulses {tot_all}")
    ncap_orc = sum(1 for v in percap.values() if v[1] > 0)
    print(f"captures with oracle-irreducible errors: {ncap_orc}/36")


if __name__ == "__main__":
    main()
