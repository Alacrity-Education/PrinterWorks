"""Fast vectorized calibration with drift: t(i,s)=i*P+drift*i^2+o_s."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0
NBITS = 192
FRAME_END = NBITS * BIT


def frame_bits(frame_hex):
    return np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"], dtype=np.int8)


def levels_at(bits, t):
    t = np.asarray(t, dtype=np.float64)
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < NBITS)
    kc = np.clip(k, 0, NBITS - 1)
    u = t - k * BIT
    thr = np.where(bits[kc] > 0, T1H, T0H)
    return np.where(ok & (u < thr), 1, 0).astype(np.int8)


def calib(samples, bits, Pgrid, driftgrid, ostep, ocenters=None, owin=None):
    its = np.array([s[0] for s in samples], dtype=np.float64)
    sls = np.array([s[1] for s in samples], dtype=np.int64)
    vs = np.array([s[2] for s in samples], dtype=np.int8)
    slot_idx = [np.where(sls == s)[0] for s in range(8)]
    best = None
    for drift in driftgrid:
        for P in Pgrid:
            base = its * P + drift * its * its
            tot = 0
            offs = []
            for s in range(8):
                idx = slot_idx[s]
                b = base[idx]
                v = vs[idx]
                if ocenters is None:
                    cand = np.arange(0.0, 2500.0, ostep)
                else:
                    cand = np.arange(ocenters[s] - owin, ocenters[s] + owin + 1e-9, ostep)
                # matrix: len(cand) x len(idx)
                tm = b[None, :] + cand[:, None]
                lv = levels_at(bits, tm)
                inframe = (tm >= -200) & (tm < FRAME_END + 700)
                g = ((lv == v[None, :]) & inframe).sum(axis=1)
                j = int(np.argmax(g))
                tot += int(g[j])
                offs.append(float(cand[j]))
            if best is None or tot > best[0]:
                best = (tot, P, drift, offs)
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    rows = []
    for c in train:
        s = linearize(c['capture'])
        bits = frame_bits(c['frame'])
        b = calib(s, bits, np.arange(2470, 2530, 2.0), [0.0], 10.0)
        b = calib(s, bits, np.arange(b[1] - 3, b[1] + 3.01, 0.25), np.arange(-0.15, 0.151, 0.03),
                  2.0, b[3], 40.0)
        b = calib(s, bits, np.arange(b[1] - 0.5, b[1] + 0.51, 0.05), np.arange(b[2] - 0.03, b[2] + 0.031, 0.005),
                  0.5, b[3], 8.0)
        n_in = len([1 for it, sl, v in s if it * b[1] + b[3][sl] < FRAME_END + 700])
        rows.append((c, b, n_in))
        print(f"{c['pattern']:11s} r{c['rep']} P={b[1]:8.2f} dr={b[2]:+6.3f} miss={n_in-b[0]:3d}/{n_in:4d} "
              f"offs={' '.join('%6.1f' % o for o in b[3])}")
    tot = sum(b[0] for _, b, _ in rows)
    totn = sum(n for _, _, n in rows)
    print(f"TOTAL {tot}/{totn} = {tot/totn:.3%}")


main()
