"""Label observed runs against the fitted timebase and measure the
pulse-width / low-gap statistics a histogram classifier would see."""
import json
from collections import Counter, defaultdict
from common import *

meta, caps = load_dataset()
A = json.load(open("align.json"))
f = A["f"]
byk = {(r["pattern"], r["rep"]): r for r in A["rows"]}

W = defaultdict(list)          # class -> list of (nsamp, width_ns, slot0)
GAP = defaultdict(list)
PULSECOUNT = []
merge_ct = Counter()
swallow_ct = Counter()
allrows = []

for c in caps:
    r = byk[(c["pattern"], c["rep"])]
    t0, L = r["t0"], r["L"]
    s = linearize(c["capture"]); bits = frame_bits(c["payload"])
    T = [t0 + (i + f[sl]) * L for i, sl, _ in s]
    rr = runs_of(s)
    nhi = sum(1 for x in rr if x[0] == 1)
    n1 = sum(bits); n0 = len(bits) - sum(bits)
    # which bits produced >=1 high sample?
    covered = Counter()
    for j, (i, sl, v) in enumerate(s):
        if v:
            k = int(T[j] // BIT)
            if 0 <= k < 192:
                covered[k] += 1
    miss1 = sum(1 for k in range(192) if bits[k] == 1 and covered[k] == 0)
    miss0 = sum(1 for k in range(192) if bits[k] == 0 and covered[k] == 0)
    swallow_ct[("1", c["pattern"])] += miss1
    swallow_ct[("0", c["pattern"])] += miss0
    # per high run: which bits it touches
    for lev, a, b, n in rr:
        w = T[b] - T[a]
        ks = sorted({int(T[j] // BIT) for j in range(a, b + 1)
                     if 0 <= T[j] < 192 * BIT})
        if lev == 1:
            if len(ks) == 1:
                cls = "1" if bits[ks[0]] else "0"
            elif len(ks) == 0:
                cls = "out"
            else:
                cls = "M" + "".join(str(bits[k]) for k in ks)
                merge_ct[cls] += 1
            W[cls].append((n, w, s[a][1], s[b][1]))
        else:
            if a == 0 or b == len(s) - 1:
                continue
            gapns = T[b + 1] - T[a - 1]
            GAP[len(ks) if ks else 0].append((n, gapns, s[a][1]))
    PULSECOUNT.append((c["pattern"], c["rep"], nhi, n1, n0, miss1, miss0))
    allrows.append(dict(pattern=c["pattern"], rep=c["rep"], nhi=nhi,
                        n1=n1, n0=n0, miss1=miss1, miss0=miss0))

print("=== high-run classes: n_samples histogram ===")
for cls in sorted(W, key=lambda k: (len(k), k)):
    h = Counter(x[0] for x in W[cls])
    ws = [x[1] for x in W[cls]]
    print(f"{cls:8s} n={len(W[cls]):5d} nsamp={dict(sorted(h.items()))}"
          f" width_ns min/med/max="
          f"{min(ws):6.0f}/{sorted(ws)[len(ws)//2]:6.0f}/{max(ws):6.0f}")

print("\n=== nsamp overlap between class 0 and class 1 ===")
h0 = Counter(x[0] for x in W["0"]); h1 = Counter(x[0] for x in W["1"])
for n in sorted(set(h0) | set(h1)):
    print(f"  nsamp={n}: zeros={h0.get(n,0):5d} ones={h1.get(n,0):5d}")

print("\n=== nsamp x start_slot for class 0 and 1 ===")
for cls in ("0", "1"):
    t = defaultdict(Counter)
    for n, w, s0, s1 in W[cls]:
        t[s0][n] += 1
    print(f" class {cls}:")
    for s0 in range(8):
        print(f"   slot0={s0}: {dict(sorted(t[s0].items()))}")

print("\n=== low gaps: n_samples by #bits spanned ===")
for k in sorted(GAP):
    h = Counter(x[0] for x in GAP[k])
    print(f" bits_spanned={k} n={len(GAP[k]):5d} nsamp={dict(sorted(h.items()))}")

print("\n=== per capture: pulses vs bits ===")
for p, rep, nhi, n1, n0, m1, m0 in PULSECOUNT:
    print(f"{p:11s} r{rep} pulses={nhi:3d} ones={n1:3d} zeros={n0:3d} "
          f"swallowed1={m1} swallowed0={m0} deficit={n1+n0-nhi}")
print("\nmerge classes:", dict(merge_ct))
json.dump(allrows, open("counts.json", "w"), indent=1)
