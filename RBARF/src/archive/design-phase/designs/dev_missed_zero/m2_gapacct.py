"""Core measurement: rise brackets, span classification, hidden-zero counts."""
from mz_common import *
from collections import Counter
import numpy as np, json

meta, caps = load()

RES = []          # rise residual (rmid - n*BIT)
DR = []           # (delta_rise/BIT, true bit advance)
WID = []          # (width, true span, true last bit)
NSAMP = []        # (nsamp_in_pulse, true span, true last bit)
hidden_hist = Counter()
hidden_run = Counter()
span_hist = Counter()
tot = Counter()
rows = []

for c in caps:
    P = prepare(c)
    t, lv, bits = P["t"], P["lv"], P["bits"]
    b = np.array(bits)
    N = len(t)
    runs = pulse_runs(lv)
    recs = []
    for i0, i1 in runs:
        if t[i0] >= NBITS * BIT + 300:
            continue
        ra = t[i0 - 1] if i0 > 0 else t[i0] - 250.0
        rb = t[i0]
        fa = t[i1]
        fb = t[i1 + 1] if i1 + 1 < N else t[i1] + 250.0
        recs.append(dict(i0=i0, i1=i1, rmid=(ra + rb) / 2, fmid=(fa + fb) / 2,
                         ra=ra, rb=rb, fa=fa, fb=fb, ns=i1 - i0 + 1))
    # ---- ground truth association: which bits' high phase overlaps this pulse
    #      (a bit's high is [k*BIT, k*BIT+T?H))
    truth = [[] for _ in recs]
    swallowed = []
    for k in range(NBITS):
        hi_lo, hi_hi = k * BIT, k * BIT + (T1H if b[k] else T0H)
        hit = None
        for m in np.nonzero((t >= hi_lo) & (t < hi_hi) & lv)[0]:
            for ri, r in enumerate(recs):
                if r["i0"] <= m <= r["i1"]:
                    hit = ri
                    break
            if hit is not None:
                break
        if hit is None:
            swallowed.append(k)
        else:
            truth[hit].append(k)
    for ri, r in enumerate(recs):
        ks = truth[ri]
        r["span"] = len(ks)
        r["n"] = ks[0] if ks else None
        r["last"] = int(b[ks[-1]]) if ks else None
        r["ksall"] = ks
    good = [r for r in recs if r["span"] > 0]
    for r in good:
        RES.append(r["rmid"] - r["n"] * BIT)
        WID.append((r["fmid"] - r["rmid"], r["span"], r["last"]))
        NSAMP.append((r["ns"], r["span"], r["last"]))
        span_hist[r["span"]] += 1
    for a, bb in zip(good, good[1:]):
        adv = bb["n"] - a["n"]
        DR.append((bb["rmid"] - a["rmid"], adv, a["span"]))
        hid = adv - a["span"]
        hidden_hist[hid] += 1
        tot["gaps"] += 1
    # runs of consecutive swallowed bits
    rl = 0
    for k in range(NBITS):
        if k in swallowed:
            rl += 1
        else:
            if rl:
                hidden_run[rl] += 1
            rl = 0
    if rl:
        hidden_run[rl] += 1
    tot["pulses"] += len(recs)
    tot["empty"] += len(recs) - len(good)
    tot["swallowed"] += len(swallowed)
    rows.append(dict(pattern=c["pattern"], rep=c["rep"], npulse=len(recs),
                     swallowed=swallowed, spans=Counter(r["span"] for r in good)))

RES = np.array(RES)
print("rise residual rmid - n*BIT : mean %.1f  std %.1f  min %.1f max %.1f  p1 %.1f p99 %.1f"
      % (RES.mean(), RES.std(), RES.min(), RES.max(), np.percentile(RES, 1), np.percentile(RES, 99)))
print("  |resid - mean| > 300ns:", int((np.abs(RES - RES.mean()) > 300).sum()), "/", len(RES))
print()
DRa = np.array([d[0] for d in DR]); ADV = np.array([d[1] for d in DR])
q = DRa / BIT
print("delta-rise/BIT vs true advance: round() correct %d/%d" % (int((np.round(q) == ADV).sum()), len(q)))
err = q - ADV
print("  frac residual: std %.4f  max|.| %.4f  p0.5 %.4f p99.5 %.4f"
      % (err.std(), np.abs(err).max(), np.percentile(err, 0.5), np.percentile(err, 99.5)))
print()
print("span histogram (true bits per visible pulse):", dict(sorted(span_hist.items())))
print("empty pulses (no true bit -> glitch):", tot["empty"])
print("hidden-zero count per gap:", dict(sorted(hidden_hist.items())))
print("swallowed run lengths:", dict(sorted(hidden_run.items())))
print("total swallowed", tot["swallowed"], "total pulses", tot["pulses"])
print()
print("width (fmid-rmid) by (span,last):")
W = {}
for w, s, l in WID:
    W.setdefault((s, l), []).append(w)
for kk in sorted(W):
    a = np.array(W[kk])
    print("  span=%d last=%d  n=%4d  mean %7.1f std %5.1f  min %7.1f max %7.1f  p1 %7.1f p99 %7.1f"
          % (kk[0], kk[1], len(a), a.mean(), a.std(), a.min(), a.max(),
             np.percentile(a, 1), np.percentile(a, 99)))
print()
print("nsamples-in-pulse by (span,last):")
NS = {}
for n, s, l in NSAMP:
    NS.setdefault((s, l), Counter())[n] += 1
for kk in sorted(NS):
    print("  span=%d last=%d : %s" % (kk[0], kk[1], dict(sorted(NS[kk].items()))))
json.dump(dict(rows=[{k: (dict(v) if isinstance(v, Counter) else v) for k, v in r.items()} for r in rows]),
          open("m2_gapacct.json", "w"), indent=1)
