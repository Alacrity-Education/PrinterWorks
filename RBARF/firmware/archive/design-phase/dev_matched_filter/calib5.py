"""Joint global fit: global slot offsets (in loop fractions) + per-capture
clock/start/drift. Coordinate descent on the global offsets."""
import sys, json
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NBITS = 192
FRAME_END = NBITS * BIT
T0H = 350.0
T1H = 700.0


def frame_bits(frame_hex):
    return np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"], dtype=np.int8)


def make_edges(bits, t0h=T0H, t1h=T1H):
    """thresholds array per bit"""
    return np.where(bits > 0, t1h, t0h)


def levels_at(thr, t):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < NBITS)
    kc = np.clip(k, 0, NBITS - 1)
    u = t - k * BIT
    return ((ok) & (u < thr[kc])).astype(np.int8)


class Cap:
    def __init__(self, c):
        s = linearize(c['capture'])
        self.pattern = c['pattern']; self.rep = c['rep']
        self.it = np.array([x[0] for x in s], dtype=np.float64)
        self.sl = np.array([x[1] for x in s], dtype=np.int64)
        self.v = np.array([x[2] for x in s], dtype=np.int8)
        self.thr = make_edges(frame_bits(c['frame']))
        self.P = 2498.0; self.d = 60.0; self.dr = 0.0

    def score(self, f, P, d, dr):
        t = self.it * P + dr * self.it * self.it + P * f[self.sl] + d
        m = t < FRAME_END + 700
        lv = levels_at(self.thr, t)
        return int(((lv == self.v) & m).sum()), int(m.sum())

    def fit(self, f, coarse=True):
        if coarse:
            Pg = np.arange(2480, 2515, 1.0); dg = np.arange(-60, 240, 15.0); drg = [0.0]
        else:
            Pg = np.arange(self.P - 2, self.P + 2.01, 0.1)
            dg = np.arange(self.d - 25, self.d + 25.01, 2.0)
            drg = np.arange(self.dr - 0.06, self.dr + 0.061, 0.02)
        best = None
        for dr in drg:
            for P in Pg:
                base = self.it * P + dr * self.it * self.it + P * f[self.sl]
                for d in dg:
                    t = base + d
                    m = t < FRAME_END + 700
                    lv = levels_at(self.thr, t)
                    g = int(((lv == self.v) & m).sum())
                    if best is None or g > best[0]:
                        best = (g, P, d, dr)
        self.P, self.d, self.dr = best[1], best[2], best[3]
        return best[0]

    def refit(self, f):
        for _ in range(2):
            Pg = np.arange(self.P - 0.6, self.P + 0.61, 0.05)
            dg = np.arange(self.d - 8, self.d + 8.01, 1.0)
            drg = np.arange(self.dr - 0.02, self.dr + 0.021, 0.005)
            best = None
            for dr in drg:
                for P in Pg:
                    base = self.it * P + dr * self.it * self.it + P * f[self.sl]
                    for d in dg:
                        t = base + d
                        m = t < FRAME_END + 700
                        lv = levels_at(self.thr, t)
                        g = int(((lv == self.v) & m).sum())
                        if best is None or g > best[0]:
                            best = (g, P, d, dr)
            self.P, self.d, self.dr = best[1], best[2], best[3]
        return best[0]


def total(caps, f):
    g = 0; n = 0
    for c in caps:
        a, b = c.score(f, c.P, c.d, c.dr)
        g += a; n += b
    return g, n


def main():
    meta, allc = load_dataset()
    train = [Cap(c) for c in allc if c['rep'] in (0, 1)]
    init = sys.argv[1] if len(sys.argv) > 1 else '0,3,8,11,16,19,24,27/40'
    pos, tot = init.split('/')
    pos = [float(x) for x in pos.split(',')]
    L = float(tot)
    f = np.array([p / L for p in pos])
    for c in train:
        c.fit(f, True)
        c.fit(f, False)
    g, n = total(train, f)
    print(f"start f={np.round(f*L,3)}  {g}/{n} = {g/n:.4%}")

    step = 0.6 / L
    for rnd in range(30):
        improved = False
        for s in range(1, 8):
            base = f[s]
            bestv = total(train, f)[0]
            bestx = base
            for delta in (-3, -2, -1, 1, 2, 3):
                f2 = f.copy(); f2[s] = base + delta * step
                v = total(train, f2)[0]
                if v > bestv:
                    bestv, bestx = v, f2[s]
            if bestx != base:
                f[s] = bestx
                improved = True
        for c in train:
            c.refit(f)
        g, n = total(train, f)
        print(f"rnd {rnd} step={step*L:.3f} f={np.round(f*L,3)} {g}/{n} = {g/n:.4%}")
        if not improved:
            step /= 2
            if step * L < 0.02:
                break
    json.dump({'f': list(f), 'L': L,
               'caps': [[c.pattern, c.rep, c.P, c.d, c.dr] for c in train]},
              open('/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_matched_filter/fit.json', 'w'))
    for c in train:
        a, b = c.score(f, c.P, c.d, c.dr)
        print(f"  {c.pattern:11s} r{c.rep} P={c.P:.2f} d={c.d:.1f} dr={c.dr:+.3f} miss={b-a}/{b}")


main()
