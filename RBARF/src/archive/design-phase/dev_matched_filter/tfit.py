"""Measure per-iteration loop start times T_i and constant slot offsets o_s.

t(i,s) = T_i + o_s.  Alternating maximization against the TRUE frame
waveform (offline diagnostic only).
"""
import sys
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
meta, allc = load_dataset()


def waveform(frame_hex):
    bits = np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"], dtype=np.int8)
    return np.where(bits > 0, 700.0, 350.0)


def lv(thr, t):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    u = t - k * BIT
    return (ok & (u < thr[kk])).astype(np.int8)


def run(pat, rep, niter=100, rounds=40, verbose=True):
    for c in allc:
        if c['pattern'] == pat and c['rep'] == rep:
            break
    s = linearize(c['capture'])
    thr = waveform(c['frame'])
    g = {}
    for it, sl, v in s:
        g[(it, sl)] = v
    L = np.array([[g.get((i, k), 0) for k in range(8)] for i in range(niter)],
                 dtype=np.int8)
    o = np.arange(8) * 312.5
    T = np.arange(niter) * float(__import__("os").environ.get("PINIT","2500"))
    win = 900.0
    for r in range(rounds):
        # --- optimize T_i (independent per iteration, constrained window)
        step = 2.0 if r < rounds - 8 else 0.5
        cand = np.arange(-win, win + 1e-9, step)
        newT = T.copy()
        for i in range(niter):
            tt = T[i] + cand
            t = tt[:, None] + o[None, :]
            m = (lv(thr, t) == L[i][None, :]).sum(axis=1)
            mx = m.max()
            js = np.where(m == mx)[0]
            newT[i] = T[i] + cand[js[len(js) // 2]]
        T = newT
        win = max(60.0, win * 0.6)
        # --- optimize o_s
        cand = np.arange(-250, 250.1, 1.0)
        for sslot in range(8):
            tt = T[:, None] + o[sslot] + cand[None, :]
            m = (lv(thr, tt.T) == L[:, sslot][None, :]).sum(axis=1)
            mx = m.max()
            js = np.where(m == mx)[0]
            o[sslot] += cand[js[len(js) // 2]]
        tot = int((lv(thr, T[:, None] + o[None, :]) == L).sum())
    if verbose:
        print(f"{pat} r{rep}: match {tot}/{niter*8} = {tot/(niter*8):.2%}")
        print("  o:", np.round(o, 1).tolist())
        print("  o cyc:", np.round(o / 62.5, 2).tolist())
        d = np.diff(T)
        print("  dT:", np.round(d, 1).tolist())
        print(f"  dT mean={d[:96].mean():.2f} std={d[:96].std():.2f}")
    return o, T, tot


if __name__ == '__main__':
    pats = sys.argv[1:] or ['zeros', 'ones', 'rnd1']
    for p in pats:
        run(p, 0)
