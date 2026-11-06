"""Work in bit-index coordinates x = (i + phi_s)*lam + beta.
Measure: (a) blind estimation of lam/beta from frame span + comb,
(b) fall-phase histogram separability, (c) discriminating-sample counts."""
import json, math
from collections import Counter, defaultdict
from common import *

meta, caps = load_dataset()
G = json.load(open("geom.json"))
o = G["o"]
LOOPNOM = 2500.0
PHI = [x / LOOPNOM for x in o]          # slot offsets in loop units
H0, H1 = 0.28, 0.56


def edges(samples):
    """rising/falling bracket pairs as sample-index intervals."""
    ev = []
    prev = samples[0][2]
    for j in range(1, len(samples)):
        v = samples[j][2]
        if v != prev:
            ev.append(("R" if v else "F", j - 1, j))
            prev = v
    return ev


def loopcoord(i, s):
    return i + PHI[s]


def blind_lam_beta(samples):
    """lam (bits per loop), beta (bit index of loop coord 0)."""
    ev = edges(samples)
    # first rise: sample (0,0) is high by construction -> bit 0 starts at
    # the last low before it; here capture starts high, so x(0,0) in [0,H*)
    firstL = loopcoord(samples[0][0], samples[0][1])
    lastF = None
    for kind, a, b in ev:
        if kind == "F":
            lastF = 0.5 * (loopcoord(*samples[a][:2]) + loopcoord(*samples[b][:2]))
    # last fall is the end of bit 191's high (trailer ends FF)
    span_loops = lastF - firstL
    lam = (191.0 + H1) / span_loops
    beta = -firstL * lam          # so that x(first sample) = 0
    return lam, beta, span_loops


rows = []
FALL = defaultdict(list)
DISC = Counter()
ERR = Counter()
for c in caps:
    s = linearize(c["capture"])
    bits = frame_bits(c["payload"])
    lam, beta, span = blind_lam_beta(s)
    X = [loopcoord(i, sl) * lam + beta for i, sl, _ in s]
    # residual check against truth
    bad = sum(1 for j, (i, sl, v) in enumerate(s)
              if (1 if (X[j] - math.floor(X[j])) <
                  (H1 if (0 <= int(X[j]) < 192 and bits[int(X[j])]) else
                   (H0 if 0 <= int(X[j]) < 192 else -1)) else 0) != v
              if 0 <= X[j] < 192)
    rows.append((c["pattern"], c["rep"], lam, beta, bad))
    # fall-phase per pulse: bracket the falling edge, take midpoint
    ev = edges(s)
    for kind, a, b in ev:
        if kind != "F":
            continue
        xm = 0.5 * (X[a] + X[b])
        k = int(math.floor(X[a]))
        if not (0 <= k < 192):
            continue
        ph = xm - k
        FALL[bits[k]].append(ph)
    # discriminating samples per bit
    for k in range(192):
        nd = 0
        wrong = 0
        for j, (i, sl, v) in enumerate(s):
            ph = X[j] - k
            if H0 <= ph < H1:
                nd += 1
                if v != bits[k]:
                    wrong += 1
        DISC[(bits[k], nd)] += 1
        if nd and wrong:
            ERR[(bits[k], nd, wrong)] += 1

print("=== blind lam/beta ===")
lams = [r[2] for r in rows]
print("lam min/med/max %.5f %.5f %.5f (loop_ns = lam^-1*1250 -> %.1f..%.1f)"
      % (min(lams), sorted(lams)[len(lams) // 2], max(lams),
         1250 / max(lams), 1250 / min(lams)))
print("residual mismatch (blind, in-frame): total",
      sum(r[4] for r in rows), " worst:",
      sorted(rows, key=lambda r: -r[4])[:6])

print("\n=== fall-phase histogram (bit units) ===")
for b in (0, 1):
    v = sorted(FALL[b])
    n = len(v)
    print(f" bit={b} n={n} p1={v[n//100]:.3f} p5={v[n//20]:.3f} "
          f"p50={v[n//2]:.3f} p95={v[-1-n//20]:.3f} p99={v[-1-n//100]:.3f}")
for th in (0.36, 0.40, 0.42, 0.44, 0.48):
    fp = sum(1 for x in FALL[0] if x > th)
    fn = sum(1 for x in FALL[1] if x <= th)
    print(f"  thr={th}: 0->1 {fp}  1->0 {fn}  err={(fp+fn)/(len(FALL[0])+len(FALL[1])):.4f}")

print("\n=== discriminating samples per bit ===")
for b in (0, 1):
    tot = sum(v for (bb, nd), v in DISC.items() if bb == b)
    h = {nd: v for (bb, nd), v in sorted(DISC.items()) if bb == b}
    print(f" bit={b} tot={tot} nd-hist={h}")
print(" inconsistent (some disc samples disagree):",
      {k: v for k, v in sorted(ERR.items())})
json.dump({"rows": [[a, b, l, bt, bd] for a, b, l, bt, bd in rows]},
          open("blind.json", "w"))
