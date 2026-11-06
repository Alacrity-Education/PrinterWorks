"""Validation report + fitted_model.json writer.

Simulates every capture from the fitted parameters and compares against
the real samples: overall / per-pattern agreement, merge-run statistics
in `ones`, swallowed-pulse counts in `zeros`.
"""
import json
import sys
from collections import defaultdict

import numpy as np

import model
from model import wire_levels, BIT_NS
import fit4

STAGE = sys.argv[1] if len(sys.argv) > 1 else "stage4.json"


def full_arrays(c, g, w):
    """A(n) over ALL 5118 samples (not just the active window)."""
    it, sl, lv = c["it"], c["sl"], c["lv"]
    n = len(it)
    Hc = np.zeros((n, 8))
    run = np.zeros(8)
    for m in range(n):
        Hc[m] = run
        run[sl[m]] += lv[m]
    g = np.asarray(g, float)
    P = np.concatenate([[0.0], np.cumsum(g)[:-1]])
    return it.astype(float) * g.sum() + P[sl] + Hc @ np.asarray(w, float)


def merge_stats(it, sl, lv, lo, hi):
    """Loops in [lo,hi) whose slot-7 sample is HIGH (inter-bit low merged
    into the slot7->slot0 gap), plus the longest consecutive run."""
    d = {}
    for i, s, v in zip(it, sl, lv):
        d[(int(i), int(s))] = int(v)
    flags = [d.get((i, 7), 0) for i in range(lo, hi)]
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return sum(flags), best, len(flags)


def swallow_count(t, bits, lv, nb):
    """0-bits of the frame that produced no HIGH sample at all."""
    b = np.floor(t / BIT_NS).astype(np.int64)
    lost = 0
    tot0 = 0
    for j in range(nb):
        if bits[j]:
            continue
        tot0 += 1
        sel = b == j
        if not sel.any() or lv[sel].max() == 0:
            lost += 1
    return lost, tot0


def main():
    d = json.load(open(STAGE))
    g, w, h1, h0 = d["g"], d["w"], d["h1"], d["h0"]
    meta, caps = model.load()
    caps = fit4.prepare(caps)

    per_pat = defaultdict(lambda: [0, 0])
    tot_m = tot_n = 0
    act_m = act_n = 0
    out_nuis = {}
    lines = []
    ones_obs, ones_sim, zeros_obs, zeros_sim = [], [], [], []
    for c in caps:
        t0, k, q = d["nuis"][c["key"]][:3]
        A = full_arrays(c, g, w)
        t = fit4.times(A, t0, k, q)
        pred = wire_levels(t, c["bits"], h1, h0)
        m = int(np.count_nonzero(pred == c["lv"]))
        n = len(c["lv"])
        tot_m += m
        tot_n += n
        act = c["it"] < fit4.ACT
        am = int(np.count_nonzero(pred[act] == c["lv"][act]))
        act_m += am
        act_n += int(act.sum())
        per_pat[c["pattern"]][0] += m
        per_pat[c["pattern"]][1] += n
        eps = 1.0 / k - 1.0
        out_nuis[c["key"]] = {"t0_ns": round(t0, 3), "eps": round(eps, 7),
                              "drift": round(q, 6)}
        lines.append(f"{c['key']:14s} all {m:5d}/{n} {100*m/n:7.3f}%   "
                     f"frame {am:4d}/{int(act.sum())} {100*am/act.sum():7.3f}%"
                     f"   eps={eps*100:+.3f}%")
        if c["pattern"] == "ones":
            ones_obs.append(merge_stats(c["it"], c["sl"], c["lv"], 8, 80))
            ones_sim.append(merge_stats(c["it"], c["sl"], pred, 8, 80))
        if c["pattern"] == "zeros":
            nb = len(c["bits"])
            zeros_obs.append(swallow_count(t, c["bits"], c["lv"], nb))
            zeros_sim.append(swallow_count(t, c["bits"], pred, nb))

    print("\n".join(lines))
    print(f"\nOVERALL  all samples  {tot_m}/{tot_n} = {100*tot_m/tot_n:.4f}%")
    print(f"OVERALL  frame window {act_m}/{act_n} = {100*act_m/act_n:.4f}%")
    print("\nper pattern (all samples):")
    for p in sorted(per_pat):
        a, b = per_pat[p]
        print(f"  {p:12s} {a:5d}/{b:5d} = {100*a/b:7.3f}%")
    print(f"\nones merged loops (count, longest run, of {ones_obs[0][2]}):")
    for i, (o, s) in enumerate(zip(ones_obs, ones_sim)):
        print(f"  rep{i}  observed {o[0]:3d} (max run {o[1]})   "
              f"simulated {s[0]:3d} (max run {s[1]})")
    print("\nzeros swallowed 0-bits (of all 0-bits in frame):")
    for i, (o, s) in enumerate(zip(zeros_obs, zeros_sim)):
        print(f"  rep{i}  observed {o[0]}/{o[1]}   simulated {s[0]}/{s[1]}")

    G = float(np.sum(g))
    P = np.concatenate([[0.0], np.cumsum(np.asarray(g, float))[:-1]])
    out = {
        "loop_ns": G,
        "slot_offsets_ns": [round(float(x), 4) for x in P],
        "eff_high_1_ns": round(float(h1), 4),
        "eff_high_0_ns": round(float(h0), 4),
        "slot_gaps_ns": [round(float(x), 4) for x in g],
        "high_sample_gap_extra_ns": [round(float(x), 4) for x in w],
        "agreement_rate": round(tot_m / tot_n, 6),
        "agreement_rate_frame_window": round(act_m / act_n, 6),
        "per_pattern_agreement": {p: round(a / b, 6)
                                  for p, (a, b) in sorted(per_pat.items())},
        "per_capture": out_nuis,
        "notes": (
            "t(i,s) = t0 + k*A(i,s), k = 1/(1+eps); "
            "A(i,s) = i*loop_ns + slot_offsets_ns[s] + sum_j "
            "high_sample_gap_extra_ns[j]*H_j(i,s), where H_j(i,s) is the "
            "number of times slot j has read HIGH strictly before sample "
            "(i,s). The w term is the extra loop time caused by a HIGH "
            "read: BTJT branches and skips its NOP, and the net cost of "
            "that code site differs by about +-1 CPU cycle. Because the "
            "loop period therefore depends on the signal being sampled, "
            "the sampler phase-locks to the WS2812 stream - which is why "
            "the 192-bit frame occupies exactly 96 loops in all 54 "
            "captures and why the merged-pulse pattern in 'ones' is a "
            "near-alternating (sigma-delta / Sturmian) sequence rather "
            "than one long consecutive run."),
    }
    json.dump(out, open("fitted_model.json", "w"), indent=1)
    print("\nwrote fitted_model.json")


if __name__ == "__main__":
    main()
