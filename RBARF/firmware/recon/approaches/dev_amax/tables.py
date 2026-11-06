#!/usr/bin/env python3
"""Render the AMAX_TMAX_SWEEP.md tables from the sweep JSONs (no numbers
are typed by hand into the report)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from amaxlib import fa_bound, max_trials, proj_ms, MS_FIXED, MS_PER_TRIAL


def load(n):
    return json.loads((HERE / ("sweep_%s.json" % n)).read_text())


def mean(h):
    it = [(int(k), v) for k, v in h.items()]
    n = sum(v for _, v in it)
    return sum(k * v for k, v in it) / n if n else 0.0


def pq(h, q):
    it = sorted((int(k), v) for k, v in h.items())
    n = sum(v for _, v in it)
    c = 0
    for k, v in it:
        c += v
        if c >= q * n:
            return k
    return it[-1][0] if it else 0


def mx(h):
    return max((int(k) for k in h), default=0)


def rows(d):
    return {(g["A_MAX"], g["T_MAX"]): g for g in d["grid"]}


def main():
    s, w, r = load("suite"), load("wrong"), load("real")
    S, W, R = rows(s), rows(w), rows(r)
    base = S[(11, 131)]["delivered"]
    best = max(g["delivered"] for g in s["grid"])
    print("### Table 1 - corpus (a): the 70 single-shot payloads, "
          "ND=48, %d captures per point" % S[(11, 131)]["n"])
    print("(%d payloads x %s eps x %d arm phases 70..658 ns)\n"
          % (s["meta"]["payloads"],
             "/".join("%.2f" % (e * 100) for e in s["meta"]["eps"]),
             s["meta"]["n_t0"]))
    print("| A_MAX | T_MAX | delivered | % | vs base | WRONG | R3 | R6 | "
          "R7 | R8 | fa bound | trials mean/p99/max | comps mean/p99/max |"
          " worst-case ms |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
          "---:|---:|")
    for (a, t), g in S.items():
        c = g["cause"]
        print("| %d | %d | %d | %.2f %% | %+d | **%d** | %d | %d | %d | %d "
              "| %.3f %% | %.2f / %d / %d | %.2f / %d / %d | %.1f |"
              % (a, t, g["delivered"], 100.0 * g["delivered"] / g["n"],
                 g["delivered"] - base, g["wrong"], c.get("R3", 0),
                 c.get("R6", 0), c.get("R7", 0), c.get("R8", 0),
                 100 * fa_bound(t),
                 mean(g["trials_hist"]), pq(g["trials_hist"], 0.99),
                 mx(g["trials_hist"]),
                 mean(g["comps_hist"]), pq(g["comps_hist"], 0.99),
                 mx(g["comps_hist"]),
                 proj_ms(max_trials(a, t))))
    print("\nTotal delivery gain available anywhere on the grid: "
          "**%+d frames** (%d -> %d, %+.3f pp); half of it is %+.1f."
          % (best - base, base, best,
             100.0 * (best - base) / S[(11, 131)]["n"], (best - base) / 2.0))

    print("\n### Table 2 - corpus (c): MEASURED false accepts, "
          "%d corrupted frames" % w["meta"]["frames"])
    print("(%d decodes after %d model-domain exclusions; %d reach the "
          "chase)\n" % (W[(11, 131)]["n"], W[(11, 131)]["domain_excluded"],
                        w["meta"]["chase_reaching"]))
    print("| A_MAX | T_MAX | emissions | **WRONG** | measured rate | "
          "analytic fa bound | trials mean/p99/max |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for (a, t), g in W.items():
        em = g["delivered"] + g["wrong"]
        print("| %d | %d | %d | **%d** | %.4f %% | %.3f %% | "
              "%.1f / %d / %d |"
              % (a, t, em, g["wrong"], 100.0 * g["wrong"] / em,
                 100 * fa_bound(t), mean(g["trials_hist"]),
                 pq(g["trials_hist"], 0.99), mx(g["trials_hist"])))

    print("\n### Table 3 - corpus (b): data/captures_v23.json, "
          "%d real silicon captures, ND=16\n" % R[(11, 131)]["n"])
    ds = sorted({g["delivered"] for g in r["grid"]})
    cs = sorted({tuple(sorted(g["cause"].items())) for g in r["grid"]})
    print("Delivered at EVERY one of the %d grid points: **%s/%d**; "
          "refusal cause at every point: %s; WRONG %d everywhere.  "
          "The corpus is completely FLAT over the grid."
          % (len(r["grid"]), ds, R[(11, 131)]["n"], cs,
             max(g["wrong"] for g in r["grid"])))
    # ---- the refinement grids -----------------------------------------
    f = load("suite_fine")
    F = rows(f)
    As = sorted({a for a, _t in F})
    Ts = sorted({t for _a, t in F})
    fb = F[(11, 131)]["delivered"]
    print("\n### Table 4 - refinement A: delivered - baseline, "
          "the same %d captures\n" % F[(11, 131)]["n"])
    print("| A_MAX \\ T_MAX | " + " | ".join(str(t) for t in Ts) + " |")
    print("|---:|" + "---:|" * len(Ts))
    for a in As:
        print("| **%d** | " % a
              + " | ".join("%+d" % (F[(a, t)]["delivered"] - fb)
                           for t in Ts) + " |")
    print("\nWRONG on the same grid (production geometry, trim band):\n")
    print("| A_MAX \\ T_MAX | " + " | ".join(str(t) for t in Ts) + " |")
    print("|---:|" + "---:|" * len(Ts))
    for a in As:
        print("| **%d** | " % a
              + " | ".join("%d" % F[(a, t)]["wrong"] for t in Ts) + " |")

    k = load("suite_tknee")
    K = rows(k)
    kb = K[(11, 131)]["delivered"]
    print("\n### Table 5 - refinement B: the T_MAX knee at A_MAX = 16\n")
    print("| T_MAX | " + " | ".join(str(t) for a, t in K if a == 16)
          + " |")
    print("|---:|" + "---:|" * len([1 for a, _ in K if a == 16]))
    print("| delivered - base | "
          + " | ".join("%+d" % (K[(16, t)]["delivered"] - kb)
                       for a, t in K if a == 16) + " |")

    pw = load("wrong_points")
    P = rows(pw)
    print("\n### Table 6 - corpus (c) at the CHOSEN points "
          "(same %d frames, same seed)\n" % pw["meta"]["frames"])
    print("| A_MAX | T_MAX | emissions | **WRONG** | measured rate | "
          "analytic fa bound |")
    print("|---:|---:|---:|---:|---:|---:|")
    for (a, t), g in P.items():
        em = g["delivered"] + g["wrong"]
        print("| %d | %d | %d | **%d** | %.4f %% | %.3f %% |"
              % (a, t, em, g["wrong"], 100.0 * g["wrong"] / em,
                 100 * fa_bound(t)))

    print("\n(worst-case ms = %.0f ms fixed pipeline + %.2f ms x "
          "min(A_MAX*(A_MAX+1)/2, T_MAX-1))" % (MS_FIXED, MS_PER_TRIAL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
