"""Bit-agnostic timing fit from rising-edge alignment to the 1250ns grid."""
import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
POS = [1, 5, 9, 13, 17, 21, 27, 32]
GAPS = [4, 4, 4, 4, 4, 6, 5, 6]


def cum_cycles(samples, gaps, delta, nfr):
    """cycle index of each sample under data-dependent gap model."""
    out = []
    c = 1.0  # slot0 of iter0 at cycle 1
    for n, (i, sl, v) in enumerate(samples):
        out.append(c)
        c += gaps[sl] + delta * v
        if n > nfr:
            break
    return out


def rise_cost(samples, cyc_pos, cyc, t0, nlim):
    """sum of squared distance from grid for each observed rising edge."""
    cost = 0.0
    cnt = 0
    prev = samples[0][2]
    for n in range(1, min(len(cyc_pos), nlim)):
        v = samples[n][2]
        if v and not prev:
            ta = t0 + cyc * cyc_pos[n - 1]
            tb = t0 + cyc * cyc_pos[n]
            ka = ta / BIT
            kb = tb / BIT
            import math
            k = math.floor(kb)
            g = k * BIT
            if g < ta:
                # no grid point inside; distance
                d = min(abs(ta - g), abs(tb - (k + 1) * BIT))
            else:
                d = 0.0
            cost += d * d
            cnt += 1
        prev = v
    return cost, cnt


def main():
    meta, caps = load_dataset()
    for c in caps:
        s = linearize(c['capture'])
        # limit to frame region: find last high sample
        lastn = max(n for n, (i, sl, v) in enumerate(s) if v)
        nlim = lastn + 2
        best = None
        for delta in (0, 1):
            cp = cum_cycles(s, GAPS, delta, nlim + 5)
            for pi in range(400):
                cyc = 61.0 + pi * 0.01
                for ti in range(-6, 7):
                    t0 = ti * 10.0
                    co, cnt = rise_cost(s, cp, cyc, t0, nlim)
                    if cnt < 20:
                        continue
                    val = co / cnt
                    if best is None or val < best[0]:
                        best = (val, delta, cyc, t0, cnt)
        val, delta, cyc, t0, cnt = best
        # implied total cycles per loop
        print(f"{c['pattern']:11s} {c['rep']} rms={val**0.5:6.1f} delta={delta} cyc={cyc:.3f} t0={t0:5.1f} nrise={cnt} lastn={lastn}")


if __name__ == '__main__':
    main()
