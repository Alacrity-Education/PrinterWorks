"""Anchors and tracking on real data.

1. Is the integer bit origin fixed by the trigger (k0 = 0)?
2. Two-anchor scale: local phase at the header (bits 0..31) vs at the
   trailer (bits 160..191) -> independent scale estimate; its noise.
3. Does a tracked (piecewise / 2nd order) phase beat a global 2-parameter
   fit on real data?  Residual vs position, per-segment phase.
4. Merged-pulse run lengths (how long the T1L vanishing episodes last).
"""
import numpy as np
from common import load_all, BIT_NS
from exp8_pipeline import A, BIAS_F, coarse, refine, sample_times

NB = 192


def truth_grid_offset(cap, phi, L):
    """Compare the model bit index of each rising edge with the true bit
    index (from ground truth) -> integer slip, if any."""
    lev = cap["lev"]
    d = np.diff(lev.astype(int))
    idx = np.nonzero(d > 0)[0]
    t = sample_times(cap, phi, L)
    tm = 0.5 * (t[idx] + t[idx + 1])
    kmod = np.round(tm / BIT_NS).astype(int)
    # true bit index: rising edge before sample idx+1 -> the bit whose start
    # is the latest true edge <= true time.  Use ground truth waveform edges.
    bits = cap["bits"]
    # true rise times are k*1250 for every k; the observed rise belongs to
    # the bit whose high pulse contains sample idx+1.
    # Recover it by counting 1-bits: use the model as reference and check
    # the level prediction consistency instead.
    return kmod


def seg_phase(cap, phi, L, nseg=6):
    lev = cap["lev"]
    d = np.diff(lev.astype(int))
    idx = np.nonzero(d > 0)[0]
    t = sample_times(cap, phi, L)
    s0 = cap["slot"][idx]
    tm = 0.5 * (t[idx] + t[idx + 1])
    m = tm < NB * BIT_NS
    tm, s0 = tm[m], s0[m]
    r = tm - np.round(tm / BIT_NS) * BIT_NS
    out = []
    for g in range(nseg):
        lo, hi = g * NB * BIT_NS / nseg, (g + 1) * NB * BIT_NS / nseg
        sel = (tm >= lo) & (tm < hi)
        out.append((np.median(r[sel]) if sel.sum() else np.nan, int(sel.sum())))
    return out


def merged_runs(cap):
    """Runs of consecutive loops in which a T1L (inter-1-bit low) is lost:
    detect high pulses longer than 1.4 bit periods."""
    lev = cap["lev"]; it = cap["it"]
    runs = []; cur = None
    prev = lev[0]; start = 0
    for n in range(1, len(lev)):
        if lev[n] != prev:
            if prev == 1:
                width = it[n] - it[start]
                if width >= 1:                # >= a full loop of high
                    runs.append(it[start])
            start = n; prev = lev[n]
    # group consecutive iterations
    groups = []
    for x in runs:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [(g[0], g[-1], len(g)) for g in groups]


if __name__ == "__main__":
    meta, caps = load_all()
    Lgrid = np.arange(2300.0, 2705.0, 2.0)
    print("== per-capture fit, segment phases (ns), header/trailer scale ==")
    print(f"{'pattern':11s} {'rep':>3s} {'L':>8s} "
          f"{'seg phase medians (6 x 32 bits)':>46s} {'L_2anchor':>9s}")
    dl = []
    for cap in caps:
        Lc, J, _ = coarse(cap, Lgrid)
        phi, L, res, k, umid, s0 = refine(cap, Lc)
        sp = seg_phase(cap, phi, L)
        ph = np.array([p for p, n in sp])
        # two-anchor scale: phase drift between first and last segment
        span = (NB * BIT_NS) * (len(sp) - 1) / len(sp)
        L2 = L * (1 + (ph[-1] - ph[0]) / span)
        dl.append(L2 - L)
        s = " ".join(f"{p:+7.1f}" for p in ph)
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {L:8.2f} {s} {L2:9.2f}")
    dl = np.array(dl)
    print(f"\nL_2anchor - L_global: mean={dl.mean():+.3f} std={dl.std():.3f} "
          f"max|.|={np.abs(dl).max():.3f} ns  "
          f"({np.abs(dl).max()/2499.6*100:.4f}% of clock)")

    print("\n== merged-pulse (T1L lost) episodes, loops ==")
    for pat in ("ones", "aa", "dense", "runs", "p55"):
        for rep in (0,):
            cap = next(c for c in caps if c["pattern"] == pat and c["rep"] == rep)
            g = merged_runs(cap)
            print(f"{pat:8s} rep{rep}: n={len(g)} "
                  f"{[(a, b, n) for a, b, n in g][:12]}")
