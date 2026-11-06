"""(a) Independent crawl estimate from merged-pulse episode lengths.
   (b) Sampling-phase diversity across the frame: near-commensurate ->
       frozen sample pattern -> per-bit systematic errors that do not
       average out.
   (c) Envelope: rises detected / bits swallowed / merges at each eps.
"""
import sys
import numpy as np
from common import load_all, BIT_NS, REC
sys.path.insert(0, str(REC))
from synth import synth_capture                        # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                          # noqa: E402
from exp9_envelope import pack

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0


def episodes(cap):
    """runs of consecutive 1-bits merged: high pulses spanning >=2 loops."""
    lev, it = cap["lev"], cap["it"]
    ep, start, prev = [], 0, lev[0]
    for n in range(1, len(lev)):
        if lev[n] != prev:
            if prev == 1 and it[n] - it[start] >= 1:
                ep.append(it[start])
            start, prev = n, lev[n]
    groups = []
    for x in ep:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [len(g) for g in groups]


if __name__ == "__main__":
    meta, caps = load_all()
    print("== merged-pulse episode lengths (loops) on 1-rich patterns ==")
    allep = []
    for cap in caps:
        if cap["pattern"] not in ("ones", "dense", "runs", "aa", "p55", "blocks"):
            continue
        e = episodes(cap)
        allep += [x for x in e if x >= 3]
        print(f"{cap['pattern']:8s} rep{cap['rep']} episodes={e}")
    allep = np.array(allep)
    print(f"\nepisodes >=3 loops: n={len(allep)} max={allep.max()} "
          f"median={np.median(allep):.0f}")
    for gap in (555., 562., 575., 600.):
        w = gap - 550.0
        print(f"  if end-of-loop gap = {gap:.0f} ns -> merge phase window "
              f"{w:5.1f} ns -> |delta| = w/len: "
              f"max-episode {w/allep.max():.3f} ns/loop  "
              f"median {w/np.median(allep):.3f} ns/loop"
              f"  => L in [{2500-w/np.median(allep):.1f}, "
              f"{2500+w/np.median(allep):.1f}]")

    print("\n== sampling-phase diversity: bit-phase of each slot over the frame ==")
    for L in (2499.8, 2507.3):
        crawl = (L - 2 * BIT_NS) * 96
        print(f"  L={L}: delta={L-2500:+.2f} ns/loop, "
              f"total crawl over 96 loops = {crawl:+.0f} ns = "
              f"{crawl/BIT_NS:+.3f} bit")

    print("\n== envelope: pulse statistics (synth) ==")
    print(f"{'eps':>8s} {'rises':>7s} {'lost0':>7s} {'merges':>7s} "
          f"{'delta ns/loop':>13s} {'crawl/frame(bit)':>17s}")
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.01, -0.002, 0.0,
                0.002, 0.01, 0.025, 0.05, 0.075):
        L = 40 * 62.5 / (1 + eps)
        nb = 192.0 * BIT_NS
        U = nb / L
        nr, lost, mg = [], [], []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=eps, phase_ns=(r*83.)%250))
                d = np.diff(cap["lev"].astype(int))
                nr.append((d > 0).sum())
                lost.append(192 - (d > 0).sum())
                mg.append(sum(episodes(cap)))
        print(f"{eps:+8.3f} {np.mean(nr):7.1f} {np.mean(lost):7.1f} "
              f"{np.mean(mg):7.1f} {L-2500:13.2f} "
              f"{(L-2500)*U/BIT_NS:17.3f}")
