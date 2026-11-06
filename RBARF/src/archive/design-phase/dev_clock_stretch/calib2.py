"""Global calibration v2: soft likelihood, fine per-capture (cyc,t0,drift) grid.

Global params: p_cyc[0..7] (slot positions in CPU cycles), L (loop cycles),
edge smear sigma, T0/T1 effective.
Per-capture: cyc (ns per cycle), t0, drift (ns per iteration^2 /2).
Only header+trailer bits used (runtime-known).
"""
import sys, json, math
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NBITS = 192


def frame_bits(hexstr):
    return [int(x) for byte in bytes.fromhex(hexstr) for x in f"{byte:08b}"]


KNOWN = [k < 32 or k >= 160 for k in range(NBITS)]


def p_high(ph, b, T0, T1, sig):
    """soft prob of high at phase ph within bit of value b."""
    Th = T1 if b else T0
    # rise at 0, fall at Th; use logistic edges
    a = 1.0 / (1.0 + math.exp(-(ph - 0.0) / sig))
    c = 1.0 / (1.0 + math.exp((ph - Th) / sig))
    return max(1e-4, min(1 - 1e-4, a * c))


LUT = None


def build_lut(T0, T1, sig, step=5.0):
    n = int(BIT / step) + 2
    lut = [[0.0] * n for _ in range(2)]
    for b in (0, 1):
        for j in range(n):
            ph = j * step
            lut[b][j] = p_high(ph, b, T0, T1, sig)
    return lut, step


def nll(samples, bits, p_cyc, L, cyc, t0, drift, lut, step, only_known=True, nlim=None):
    tot = 0.0
    cnt = 0
    lp = math.log
    tmax = NBITS * BIT
    for i, sl, v in samples:
        t = t0 + (i * L + p_cyc[sl]) * cyc + 0.5 * i * i * drift
        if t < -200:
            continue
        if t >= tmax + 600:
            break
        k = int(t // BIT)
        if k >= NBITS:
            ph = None
            pr = 1e-4
        else:
            if only_known and not KNOWN[k]:
                continue
            ph = t - k * BIT
            pr = lut[bits[k]][int(ph / step)]
        tot -= lp(pr if v else 1.0 - pr)
        cnt += 1
    return tot, cnt


def fit_capture(samples, bits, p_cyc, L, lut, step, cyc_lo=61.8, cyc_hi=63.4):
    best = None
    ncyc = int((cyc_hi - cyc_lo) / 0.005)
    for a in range(ncyc):
        cyc = cyc_lo + a * 0.005
        for ti in range(-12, 13):
            t0 = ti * 6.0
            v, _ = nll(samples, bits, p_cyc, L, cyc, t0, 0.0, lut, step)
            if best is None or v < best[0]:
                best = (v, cyc, t0, 0.0)
    v, cyc, t0, drift = best
    steps = [0.002, 3.0, 0.002]
    for _ in range(120):
        imp = False
        for idx, st in enumerate(steps):
            for d in (st, -st):
                c = [cyc, t0, drift]
                c[idx] += d
                v2, _ = nll(samples, bits, p_cyc, L, c[0], c[1], c[2], lut, step)
                if v2 < v - 1e-9:
                    v, cyc, t0, drift = v2, c[0], c[1], c[2]
                    imp = True
        if not imp:
            steps = [x * 0.5 for x in steps]
            if steps[0] < 1e-4:
                break
    return v, cyc, t0, drift


def main():
    meta, caps = load_dataset()
    data = []
    for c in caps:
        if c['rep'] == 2:
            continue
        data.append((linearize(c['capture']), frame_bits(c['frame']), c['pattern'], c['rep']))
    p_cyc = [1.0, 5.0, 9.0, 13.0, 17.0, 21.0, 27.0, 32.0]
    L = 40.0
    T0, T1, sig = 350.0, 700.0, 60.0
    lut, step = build_lut(T0, T1, sig)
    params = [None] * len(data)

    def full(pc, Lv, lu, st):
        tot = 0.0
        for j, (s, bits, pat, rep) in enumerate(data):
            r = fit_capture(s, bits, pc, Lv, lu, st)
            params[j] = r
            tot += r[0]
        return tot

    cur = full(p_cyc, L, lut, step)
    print("init nll", round(cur, 1), flush=True)

    def cost_fixed(pc, Lv, lu, st):
        tot = 0.0
        for j, (s, bits, pat, rep) in enumerate(data):
            _, cyc, t0, dr = params[j]
            # allow small local re-fit of cyc/t0 only
            bv = None
            for dc in (-0.006, -0.003, 0.0, 0.003, 0.006):
                for dt in (-6.0, -3.0, 0.0, 3.0, 6.0):
                    v, _ = nll(s, bits, pc, Lv, cyc + dc, t0 + dt, dr, lu, st)
                    if bv is None or v < bv:
                        bv = v
            tot += bv
        return tot

    stepv = 1.0
    while stepv > 0.03:
        imp = False
        for k in range(8):
            for d in (stepv, -stepv):
                pc = list(p_cyc)
                pc[k] += d
                c2 = cost_fixed(pc, L, lut, step)
                if c2 < cur - 1e-6:
                    cur, p_cyc = c2, pc
                    imp = True
        for d in (stepv, -stepv):
            c2 = cost_fixed(p_cyc, L + d, lut, step)
            if c2 < cur - 1e-6:
                cur, L = c2, L + d
                imp = True
        if not imp:
            stepv *= 0.5
        print(f"  step={stepv:.3f} cur={cur:.1f} L={L:.3f} p=" +
              " ".join(f"{x:.2f}" for x in p_cyc), flush=True)

    cur = full(p_cyc, L, lut, step)
    print("refit nll", round(cur, 1), flush=True)
    # now tune T0,T1,sig
    for _ in range(3):
        bestg = (cur, T0, T1, sig)
        for dT0 in (-40, -20, 0, 20, 40):
            for dT1 in (-40, -20, 0, 20, 40):
                for sg in (30, 45, 60, 80, 100):
                    lu, st = build_lut(T0 + dT0, T1 + dT1, sg)
                    c2 = cost_fixed(p_cyc, L, lu, st)
                    if c2 < bestg[0]:
                        bestg = (c2, T0 + dT0, T1 + dT1, sg)
        cur, T0, T1, sig = bestg
        lut, step = build_lut(T0, T1, sig)
        print("  T0", T0, "T1", T1, "sig", sig, "cur", round(cur, 1), flush=True)
        cur = full(p_cyc, L, lut, step)

    print(json.dumps({'p_cyc': p_cyc, 'L': L, 'T0': T0, 'T1': T1, 'sig': sig}))
    # report hard error rate with final params
    tot = totn = 0
    for j, (s, bits, pat, rep) in enumerate(data):
        _, cyc, t0, dr = params[j]
        e = n = 0
        for i, sl, v in s:
            t = t0 + (i * L + p_cyc[sl]) * cyc + 0.5 * i * i * dr
            if t < -200:
                continue
            if t >= NBITS * BIT + 600:
                break
            k = int(t // BIT)
            if k >= NBITS:
                lev = 0
            else:
                if not KNOWN[k]:
                    continue
                ph = t - k * BIT
                lev = 1 if ph < (T1 if bits[k] else T0) else 0
            n += 1
            e += (lev != v)
        tot += e
        totn += n
        print(f"{pat:11s} {rep} err={e:3d}/{n} cyc={cyc:.4f} P={L*cyc:8.2f} t0={t0:6.1f} dr={dr:.4f}")
    print("TOTAL", tot, totn, tot / totn)


if __name__ == '__main__':
    main()
