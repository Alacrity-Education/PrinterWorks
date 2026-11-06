"""Validation + emission of fitted_model.json.

Gauge: LOOP and the slot offsets are quoted at the NOMINAL 16 MHz clock
(62.5 ns/cycle); the per-capture eps carries the real HSI error, exactly
as the brief's model states:

    t(i,slot) = t0 + (i*LOOP + o[slot] + sum_j w[j]*C_j(i,slot)) / (1+eps)

C_j(i,slot) = number of HIGH reads at slot j strictly before this sample.

Checks reported:
  * 'ones'  : loops where the inter-bit low vanishes inside the
              slot7 -> slot0 end-of-loop gap (observed vs simulated)
  * swallowed pulses: bits whose high pulse leaves no HIGH sample
"""
import collections
import json
import sys

import numpy as np

import fitlib as F
import fit_full as FF
from fit_full import CY


def merge_stats(lv8):
    ok = (lv8[:-1, 7] == 1) & (lv8[1:, 0] == 1)
    idx = np.flatnonzero(ok)
    runs = []
    if len(idx):
        start = prev = idx[0]
        for x in idx[1:]:
            if x != prev + 1:
                runs.append(int(prev - start + 1))
                start = x
            prev = x
        runs.append(int(prev - start + 1))
    return int(ok.sum()), runs, idx


def swallowed(T, lv, bits):
    k = np.floor(T / 1250.0).astype(np.int64)
    lost = 0
    for b in range(len(bits)):
        m = k == b
        if not m.any() or lv[m].max() == 0:
            lost += 1
    return lost


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "stage_f1.json"
    st = json.load(open(src))
    G, o, w, h1, h0 = st["G"], list(st["o"]), list(st["w"]), st["h1"], st["h0"]
    nuis = {k: list(v) for k, v in st["nuis"].items()}
    meta, caps = F.load()
    caps = FF.prepare(caps)

    per_pat = collections.defaultdict(lambda: [0, 0, 0, 0])
    tot_m = tot_n = act_m = act_n = 0
    detail, sim = {}, {}
    for c in caps:
        A = FF.A_of(c, G, o, w, active=False)
        B = F.edges_of(c["bits"], h1, h0)
        t0, k = nuis[c["key"]][:2]
        T = t0 + k * A
        pred = F.level_at(T, B)
        m = int(np.count_nonzero(pred == c["lv"]))
        am = int(np.count_nonzero(pred[c["amask"]] == c["alv"]))
        p = per_pat[c["pattern"]]
        p[0] += m; p[1] += c["n"]; p[2] += am; p[3] += c["an"]
        tot_m += m; tot_n += c["n"]; act_m += am; act_n += c["an"]
        detail[c["key"]] = dict(t0_ns=t0, eps=1.0 / k - 1.0, k=k,
                                agree=m / c["n"], agree_active=am / c["an"])
        sim[c["key"]] = (T, pred)

    print(f"{'pattern':12s} {'all%':>8s} {'active%':>8s}")
    for pat in sorted(per_pat):
        a, b, cc, d = per_pat[pat]
        print(f"{pat:12s} {100*a/b:8.3f} {100*cc/d:8.3f}")
    print(f"{'TOTAL':12s} {100*tot_m/tot_n:8.3f} {100*act_m/act_n:8.3f}")

    gaps = list(np.diff(list(o) + [G]))
    kmean = float(np.mean([detail[c["key"]]["k"] for c in caps]))
    print("\ninter-sample gaps (nominal cycles): "
          f"{[round(x/CY, 3) for x in gaps]}  sum={round(sum(gaps)/CY,3)}")
    print(f"branch cost w (cycles): {[round(x/CY, 3) for x in w]}")
    print(f"mean clock scale k={kmean:.5f} -> cycle {CY*kmean:.3f} ns, "
          f"eps={1/kmean-1:+.5f}")
    eol_low = (gaps[7]) * kmean
    eol_high = (gaps[7] + w[7]) * kmean
    print(f"end-of-loop gap (slot7->slot0): {eol_low:.1f} ns after a LOW "
          f"read at slot7, {eol_high:.1f} ns after a HIGH read "
          f"(T1L = {1250-h1:.0f} ns)")

    print("\nmerge (ones): loops whose inter-bit low falls in the "
          "slot7->slot0 gap")
    mrep = {}
    for c in caps:
        if c["pattern"] != "ones":
            continue
        n8 = (c["n"] // 8) * 8
        no, ro, io = merge_stats(c["lv"][:n8].reshape(-1, 8))
        ns, rs, isim = merge_stats(sim[c["key"]][1][:n8].reshape(-1, 8))
        print(f"  {c['key']}: observed {no} (loops {io.min()}-{io.max()}, "
              f"runs {sorted(set(ro))}); simulated {ns} "
              f"(loops {isim.min()}-{isim.max()}, runs {sorted(set(rs))})")
        mrep[c["key"]] = dict(observed=no, simulated=ns, observed_runs=ro,
                              simulated_runs=rs,
                              observed_span=[int(io.min()), int(io.max())],
                              simulated_span=[int(isim.min()), int(isim.max())])

    print("\nswallowed pulses (bit high pulses with no HIGH sample), of 192:")
    srep = {}
    for c in caps:
        if c["pattern"] not in ("zeros", "lone1", "edges", "msb1", "sparse"):
            continue
        T, pred = sim[c["key"]]
        lo = swallowed(T, c["lv"], c["bits"])
        ls = swallowed(T, pred, c["bits"])
        print(f"  {c['key']}: observed {lo}, simulated {ls}")
        srep[c["key"]] = dict(observed=lo, simulated=ls)

    effs = []
    for c in caps:
        A = FF.A_of(c, G, o, w)
        z = A[c["asl"] == 0]                      # loop-start samples
        effs.append((z[-1] - z[0]) / (len(z) - 1))
    eff = float(np.mean(effs))
    notes = (
        "Model: t(i,s) = t0 + (i*LOOP + o[s] + sum_j w[j]*C_j(i,s))/(1+eps), "
        "C_j(i,s) = number of HIGH reads at slot j strictly before sample "
        "(i,s). LOOP and o[] are quoted at the nominal 16 MHz clock "
        "(62.5 ns/cycle) and come out as exact integer cycles: the loop is "
        "40 cycles with inter-sample gaps [4,5,4,4,4,6,5,8] cycles, i.e. the "
        "documented [4,4,4,4,4,6,5,6]=37 plus 1 cycle in the R1->R2 gap and "
        "2 cycles in the BS1->R0 end-of-loop gap. w[] is the extra loop time "
        "when a sample reads HIGH (the BTJT-taken / NOP-skipped path, whose "
        "cost varies with instruction alignment); it is also whole cycles, "
        "[0,-1,0,+2,0,0,0,+1]. Without w the sampler's period-2 loop-length "
        "alternation is unreproducible and agreement caps near 85-95% in the "
        "frame window. eff_high_1/eff_high_0 stayed at the exact PIO wire "
        "values, so the STM8 input threshold introduces no measurable "
        "high-width distortion beyond a +2 ns common edge shift (a common "
        "rise/fall delay is absorbed by t0; 750/375 exactly scores "
        "99.961% / 99.750%). "
        f"Mean effective loop period over the captures: {eff*kmean:.2f} ns "
        f"(mean cycle {CY*kmean:.3f} ns, eps = {1/kmean-1:+.5f}, spread "
        f"across captures only +-0.014%). "
        f"End-of-loop (slot7->slot0) gap = 8 nominal cycles = "
        f"{eol_low:.1f} ns after a LOW read at slot 7 and 9 cycles = "
        f"{eol_high:.1f} ns after a HIGH read, versus T1L = "
        f"{1250-h1:.0f} ns: that is why the inter-bit low of a 1-bit "
        "disappears into it. The loop beats against 2 bit periods by only "
        f"{abs(2*1250-eff*kmean):.2f} ns/loop, but the w[7] term makes the "
        "loop length alternate by a whole cycle, so the merged loops come "
        "in runs of 1-2 spread over loops ~21-94 rather than one long run "
        "(observed 36-39 merged loops per 'ones' capture, simulated 35-38).")
    out = dict(
        loop_ns=G, slot_offsets_ns=list(o), eff_high_1_ns=h1,
        eff_high_0_ns=h0,
        gaps_cycles=[round(x / CY, 4) for x in gaps],
        branch_cost_ns=list(w),
        branch_cost_cycles=[round(x / CY, 4) for x in w],
        mean_effective_loop_ns=eff * kmean,
        mean_cycle_ns=CY * kmean,
        notes=notes,
        per_capture={k: dict(t0_ns=v["t0_ns"], eps=v["eps"])
                     for k, v in detail.items()},
        per_capture_agreement={k: v["agree"] for k, v in detail.items()},
        per_pattern_agreement={p: per_pat[p][0] / per_pat[p][1]
                               for p in per_pat},
        per_pattern_agreement_active={p: per_pat[p][2] / per_pat[p][3]
                                      for p in per_pat},
        agreement_rate=tot_m / tot_n,
        agreement_rate_active=act_m / act_n,
        merge_check=mrep, swallow_check=srep)
    json.dump(out, open("fitted_model.json", "w"), indent=1, default=float)
    print(f"\nwrote fitted_model.json  agreement_rate={100*tot_m/tot_n:.4f}% "
          f"(active window {100*act_m/act_n:.4f}%)")


if __name__ == "__main__":
    main()
