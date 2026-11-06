"""End-to-end v2.1 single-shot evaluation on synthetic captures.

Builds real v2.1 frames (DATA || [C,C,C], CRC8/SMBUS over DATA), runs the
votes-CUT integer decoder, then the CRC8 confidence chase, and classifies
every capture as DIRECT / CHASE / REFUSE / CATASTROPHIC.
"""
import sys, pathlib, pickle, argparse
from collections import Counter, defaultdict

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
sys.path.insert(0, str(R.parent / "bench"))
from patterns import PATTERNS, VAL_PATTERNS         # noqa: E402
from synth import synth_capture                     # noqa: E402
import ref_marg as ref                              # noqa: E402
import v21                                          # noqa: E402

ref.VOTES = False
ND = 16
ref._configure(ND + 3)
NPP = ND + 3

# measured trim-code eps (TRIM_SWEEP.md) + envelope corners
TRIM_EPS = {0: -0.01072, 1: -0.02248, 2: -0.03281, 3: -0.04385,
            4: +0.03733, 5: +0.02492, 6: +0.01274, 7: +0.00022}
ENV_EPS = [-0.08, -0.075, -0.05, -0.025, -0.01, 0.0,
           0.01, 0.025, 0.05, 0.075, 0.08]
CACHE = pathlib.Path(__file__).with_name("e2e_cache.pkl")


def gather(eps_list, reps=3):
    """Decode once per (eps, pattern, rep); cache bits+mgv+gates."""
    out = {}
    if CACHE.exists():
        out = pickle.load(CACHE.open("rb"))
    todo = [(e, n, r) for e in eps_list for n in PATTERNS for r in range(reps)
            if (round(e, 6), n, r) not in out]
    for i, (eps, name, rep) in enumerate(todo):
        payload = PATTERNS[name][:ND]
        pp = v21.payload_v21(payload)
        phase = 254.0 + (rep * 83.0) % 250.0
        samples = synth_capture(pp, eps=eps, drift=0.0, phase_ns=phase)
        try:
            st = ref.decode_state(samples)
        except Exception:
            st = None
        if st is None:
            rec = None
        else:
            bits, mgv = st["bits"], st["mgv"]
            viol = sum(1 for t in range(ref.NB)
                       if ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t])
            gate = (viol > 0 or st["infeasible"] > ref.GATE_INFEAS
                    or st["label_err"] > ref.GATE_LABERR)
            rec = (bits[32:32 + NPP * 8], mgv[32:32 + NPP * 8], gate)
        out[(round(eps, 6), name, rep)] = (rec, bytes(payload))
        if i % 25 == 0:
            print("  ... %d/%d" % (i, len(todo)), flush=True)
    pickle.dump(out, CACHE.open("wb"))
    return out


def evaluate(recs, keys, **kw):
    c = Counter()
    trials = []
    detail = []
    for k in keys:
        rec, truth = recs[k]
        if rec is None or rec[2]:
            c["refuse_gate"] += 1
            continue
        bits, mgv, _ = rec
        got, nt, path = v21.chase(bits, mgv, ND, **kw)
        trials.append(nt)
        if got is None:
            c["refuse_chase"] += 1
            detail.append((k, "refuse", path, nt))
        elif got == truth:
            c["ok_" + path] += 1
        else:
            c["CATASTROPHIC_" + path] += 1
            detail.append((k, "CATASTROPHIC", path, nt))
    return c, trials, detail


def report(tag, c, trials, n):
    ok = c["ok_direct"] + c["ok_chase"] + c["ok_fallback"]
    cat = sum(v for k, v in c.items() if k.startswith("CATA"))
    ref_ = c["refuse_gate"] + c["refuse_chase"]
    print("%-34s n=%3d  delivered %3d (%5.1f%%)  [direct %3d + chase %3d + fb %d]"
          "  refuse %3d (gate %d / chase %d)  CATASTROPHIC %d  trials mean %.1f max %d"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["ok_fallback"], ref_, c["refuse_gate"], c["refuse_chase"], cat,
             sum(trials) / max(1, len(trials)), max(trials) if trials else 0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="trim")
    a = ap.parse_args()
    eps_list = (sorted(TRIM_EPS.values()) if a.mode == "trim" else ENV_EPS)
    recs = gather(eps_list)
    allk = [k for k in recs if k[0] in [round(e, 6) for e in eps_list]]
    print("\n=== budget sweep, all eps pooled (n=%d) ===" % len(allk))
    for N_CAND, W, T in ((4, 2, 11), (8, 1, 9), (8, 2, 37), (8, 3, 93),
                         (12, 2, 79), (12, 3, 299), (16, 3, 697)):
        c, tr, _ = evaluate(recs, allk, N_CAND=N_CAND, WMAX=W, TMAX=T)
        report("N=%2d W<=%d T=%3d" % (N_CAND, W, T), c, tr, len(allk))
    print("\n=== per eps, N=8 W<=3 T=93 ===")
    for e in eps_list:
        ks = [k for k in allk if k[0] == round(e, 6)]
        c, tr, d = evaluate(recs, ks, N_CAND=8, WMAX=3, TMAX=93)
        report("eps %+7.3f%%" % (e * 100), c, tr, len(ks))
        for x in d:
            print("      ", x)
