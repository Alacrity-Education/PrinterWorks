"""Fast test of the data-dependent-timing hypothesis (vectorized over b0).

  t(i,s)     = base_i + C*(pos[s] + delta*cum_ind(i,s))
  base_{i+1} = base_i + C*(ploop + delta*IND_i)

ind = the sampled level (or its complement), i.e. the hypothesis that the
sample-and-pack instruction sequence costs one extra CPU cycle when the pin
reads high (or low).  Free per capture: C (ns/cycle) and base_0 only.
"""
import sys
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
meta, allc = load_dataset()
NL = 97


def prep(c):
    s = linearize(c['capture'])
    lv = np.zeros((NL, 8), dtype=np.int8)
    for it, sl, v in s:
        if it < NL:
            lv[it, sl] = v
    bits = np.array([int(b) for byte in bytes.fromhex(c['frame'])
                     for b in f"{byte:08b}"], dtype=np.int8)
    thr = np.where(bits > 0, 700.0, 350.0)
    return lv, thr


def lvl(thr, t):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    u = t - k * BIT
    return (ok & (u < thr[kk])).astype(np.int8)


B0 = np.arange(-160, 260.1, 4.0)


def best_for(lv, thr, pos, ploop, delta, use_low, Cs):
    ind = (1 - lv) if use_low else lv
    cum = np.concatenate([np.zeros((NL, 1), dtype=np.int64),
                          np.cumsum(ind, axis=1)[:, :-1]], axis=1)
    H = ind.sum(axis=1)
    pos = np.asarray(pos, dtype=np.float64)
    best = (-1, None, None)
    for C in Cs:
        inc = C * (ploop + delta * H)
        base = np.concatenate([[0.0], np.cumsum(inc[:-1])])
        t0 = base[:, None] + C * (pos[None, :] + delta * cum)
        t = t0[None, :, :] + B0[:, None, None]
        m = (lvl(thr, t) == lv[None, :, :]).sum(axis=(1, 2))
        j = int(np.argmax(m))
        if m[j] > best[0]:
            best = (int(m[j]), float(C), float(B0[j]))
    return best


POS = {
    'doc': [1, 5, 9, 13, 17, 21, 27, 32],
    'unif': [1, 5, 9, 13, 17, 21, 25, 29],
}
train = [c for c in allc if c['rep'] in (0, 1)]
prepped = [(c, prep(c)) for c in train]
Cs = np.arange(61.0, 64.51, 0.01)
res = []
for pname, pos in POS.items():
    for ploop in (37, 38, 39, 40):
        for delta in (0, 1, 2):
            for use_low in (False, True):
                if delta == 0 and use_low:
                    continue
                G = N = 0
                worst = 1.0
                for c, (lv, thr) in prepped:
                    b = best_for(lv, thr, pos, ploop, delta, use_low, Cs)
                    G += b[0]
                    N += NL * 8
                    worst = min(worst, b[0] / (NL * 8))
                print(f"pos={pname:6s} loop={ploop} d={delta} low={int(use_low)}"
                      f"  {G}/{N} = {G/N:.3%} worst={worst:.1%}", flush=True)
                res.append((G / N, pname, ploop, delta, use_low))
res.sort(reverse=True)
print("TOP:", res[:5])
