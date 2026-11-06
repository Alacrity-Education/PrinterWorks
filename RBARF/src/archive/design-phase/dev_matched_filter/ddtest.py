"""Test the data-dependent-timing hypothesis:

  t(i,s) = base_i + C*(pos[s] + delta*cum_high(i,s))
  base_{i+1} = base_i + C*(37 + delta*H_i)

with cum_high(i,s) = # high samples in iteration i before slot s, H_i the
total.  Only C (ns/cycle) and base_0 are free per capture.
"""
import sys, itertools
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
meta, allc = load_dataset()


def prep(c):
    s = linearize(c['capture'])
    lv = np.zeros((110, 8), dtype=np.int8)
    for it, sl, v in s:
        if it < 110:
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


def score(lv, thr, pos, ploop, delta, use_low, C, b0, nl=97):
    L = lv[:nl]
    ind = (1 - L) if use_low else L
    cum = np.concatenate([np.zeros((nl, 1), dtype=np.int64),
                          np.cumsum(ind, axis=1)[:, :-1]], axis=1)
    H = ind.sum(axis=1)
    # base_i
    base = np.empty(nl)
    base[0] = b0
    inc = C * (ploop + delta * H)
    base[1:] = b0 + np.cumsum(inc[:-1])
    t = base[:, None] + C * (np.asarray(pos)[None, :] + delta * cum)
    return int((lvl(thr, t) == L).sum()), nl * 8


POS = {
    'doc': [1, 5, 9, 13, 17, 21, 27, 32],
    'unif': [1, 5, 9, 13, 17, 21, 25, 29],
    'doc2': [1, 5, 9, 13, 17, 21, 26, 31],
}
train = [c for c in allc if c['rep'] in (0, 1)]
prepped = [(c, prep(c)) for c in train]

results = []
for pname, pos in POS.items():
    for ploop in (37, 40):
        for delta in (0, 1):
            for use_low in (False, True):
                if delta == 0 and use_low:
                    continue
                G = N = 0
                per = []
                for c, (lv, thr) in prepped:
                    best = 0
                    for C in np.arange(61.0, 64.51, 0.02):
                        for b0 in np.arange(-120, 200, 10.0):
                            g, n = score(lv, thr, pos, ploop, delta, use_low, C, b0)
                            if g > best:
                                best = g; bC, bb = C, b0
                    # refine
                    for C in np.arange(bC - 0.03, bC + 0.031, 0.005):
                        for b0 in np.arange(bb - 12, bb + 12.1, 1.0):
                            g, n = score(lv, thr, pos, ploop, delta, use_low, C, b0)
                            if g > best:
                                best = g; bC2, bb2 = C, b0
                    G += best; N += n
                    per.append(best / n)
                print(f"pos={pname:5s} loop={ploop} delta={delta} low={int(use_low)}"
                      f"  match {G}/{N} = {G/N:.3%}  worst={min(per):.1%}", flush=True)
                results.append((G / N, pname, ploop, delta, use_low))
results.sort(reverse=True)
print("BEST:", results[0])
