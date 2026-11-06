"""Joint global fit, fully vectorized.

Model: t(i,s) = i*P + dr*i^2 + P*f[s] + d
Global: f[0..7] (f[0]=0), high widths w0,w1.
Per capture: P, d, dr.
"""
import sys, json
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NBITS = 192
FRAME_END = NBITS * BIT


def frame_bits(frame_hex):
    return np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"], dtype=np.int8)


class Cap:
    __slots__ = ('pattern', 'rep', 'it', 'it2', 'sl', 'v', 'bits', 'thr',
                 'P', 'd', 'dr')

    def __init__(self, c):
        s = linearize(c['capture'])
        self.pattern = c['pattern']; self.rep = c['rep']
        self.it = np.array([x[0] for x in s], dtype=np.float64)
        self.it2 = self.it * self.it
        self.sl = np.array([x[1] for x in s], dtype=np.int64)
        self.v = np.array([x[2] for x in s], dtype=np.int8)
        self.bits = frame_bits(c['frame'])
        self.thr = None
        self.P = 2498.0; self.d = 60.0; self.dr = 0.0

    def set_w(self, w0, w1):
        self.thr = np.where(self.bits > 0, w1, w0)

    def match(self, t):
        """t: array (..., N) -> match counts over last axis"""
        k = np.floor(t * (1.0 / BIT)).astype(np.int64)
        ok = (k >= 0) & (k < NBITS)
        kc = np.clip(k, 0, NBITS - 1)
        u = t - k * BIT
        lv = (ok & (u < self.thr[kc])).astype(np.int8)
        inb = t < FRAME_END + 700
        return ((lv == self.v) & inb).sum(axis=-1)

    def n_in(self):
        t = self.it * self.P + self.dr * self.it2 + self.P * np.array([0.0] * 1)[0]
        return int((self.it * self.P < FRAME_END + 700).sum())

    def grid_fit(self, f, Pg, dg, drg):
        fo = f[self.sl]
        best = (-1, self.P, self.d, self.dr)
        for dr in drg:
            b0 = self.dr_base(dr)
            # shape [nP, N]
            base = self.it[None, :] * Pg[:, None] + b0[None, :] + Pg[:, None] * fo[None, :]
            t = base[:, None, :] + dg[None, :, None]
            m = self.match(t)          # [nP, nd]
            j = int(np.argmax(m))
            ip, jd = divmod(j, len(dg))
            if m[ip, jd] > best[0]:
                best = (int(m[ip, jd]), float(Pg[ip]), float(dg[jd]), float(dr))
        self.P, self.d, self.dr = best[1], best[2], best[3]
        return best[0]

    def dr_base(self, dr):
        return dr * self.it2

    def score(self, f):
        t = self.it * self.P + self.dr * self.it2 + self.P * f[self.sl] + self.d
        return int(self.match(t)), int((t < FRAME_END + 700).sum())


def total(caps, f):
    g = n = 0
    for c in caps:
        a, b = c.score(f)
        g += a; n += b
    return g, n


def fit_all(caps, f, coarse):
    if coarse:
        Pg = np.arange(2480, 2515, 0.5)
        dg = np.arange(-80, 260, 6.0)
        drg = np.arange(-0.06, 0.061, 0.03)
    else:
        drg = None
    tot = 0
    for c in caps:
        if coarse:
            c.grid_fit(f, Pg, dg, drg)
        Pg2 = np.arange(c.P - 1.0, c.P + 1.01, 0.05)
        dg2 = np.arange(c.d - 12, c.d + 12.01, 1.0)
        drg2 = np.arange(c.dr - 0.03, c.dr + 0.031, 0.0075)
        tot += c.grid_fit(f, Pg2, dg2, drg2)
    return tot


def main():
    meta, allc = load_dataset()
    caps = [Cap(c) for c in allc if c['rep'] in (0, 1)]
    spec = sys.argv[1] if len(sys.argv) > 1 else '0,3,8,11,16,19,24,27/40'
    w0 = float(sys.argv[2]) if len(sys.argv) > 2 else 350.0
    w1 = float(sys.argv[3]) if len(sys.argv) > 3 else 700.0
    pos, L = spec.split('/'); L = float(L)
    f = np.array([float(x) / L for x in pos.split(',')])
    for c in caps:
        c.set_w(w0, w1)
    g = fit_all(caps, f, True)
    n = total(caps, f)[1]
    print(f"init pos={np.round(f*L,3)} w=({w0},{w1}) {g}/{n} = {g/n:.4%}", flush=True)

    step = 1.0 / L
    for rnd in range(40):
        improved = False
        cur = total(caps, f)[0]
        for s in range(1, 8):
            base = f[s]
            bestv, bestx = cur, base
            for delta in (-2, -1, 1, 2):
                f2 = f.copy(); f2[s] = base + delta * step
                v = total(caps, f2)[0]
                if v > bestv:
                    bestv, bestx = v, f2[s]
            if bestx != base:
                f[s] = bestx
                cur = bestv
                improved = True
        fit_all(caps, f, False)
        g, n = total(caps, f)
        print(f"rnd{rnd} st={step*L:.3f} pos={np.round(f*L,3)} {g}/{n}={g/n:.4%}", flush=True)
        if not improved:
            step /= 2.0
            if step * L < 0.03:
                break
    json.dump({'f': [float(x) for x in f], 'L': L, 'w0': w0, 'w1': w1,
               'caps': [[c.pattern, c.rep, c.P, c.d, c.dr] for c in caps]},
              open(f'/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_matched_filter/fit_{int(w0)}_{int(w1)}.json', 'w'))
    for c in caps:
        a, b = c.score(f)
        print(f"  {c.pattern:11s} r{c.rep} P={c.P:.2f} d={c.d:5.1f} dr={c.dr:+.4f} miss={b-a:3d}/{b}")


main()
