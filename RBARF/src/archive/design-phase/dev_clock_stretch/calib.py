"""Global calibration of slot offsets + effective edge times.

Uses ONLY header/trailer bits (known to the decoder at runtime).
Per-capture nuisance params: P (loop period), t0, drift.
Global params: pos_ns[8] (slot offsets at P=2500), T0 fall, T1 fall.
"""
import sys, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NBITS = 192
HDR = 32
TRL_START = 160


def frame_bits(hexstr):
    return [int(x) for byte in bytes.fromhex(hexstr) for x in f"{byte:08b}"]


def known_mask():
    m = [False] * NBITS
    for k in range(HDR):
        m[k] = True
    for k in range(TRL_START, NBITS):
        m[k] = True
    return m


MASK = known_mask()


def build_ref(bits, T0, T1):
    """list of (rise, fall) per bit."""
    return [(k * BIT, k * BIT + (T1 if bits[k] else T0)) for k in range(len(bits))]


def sample_err(samples, bits, pos_ns, P, t0, drift, T0, T1, only_known=True):
    sc = P / 2500.0
    e = 0
    n = 0
    tmax = NBITS * BIT
    for i, sl, v in samples:
        t = t0 + i * P + 0.5 * i * i * drift + pos_ns[sl] * sc
        if t < -300:
            continue
        if t >= tmax + 800:
            break
        k = int(t // BIT)
        if k >= NBITS:
            lev = 0
        else:
            if only_known and not MASK[k]:
                continue
            ph = t - k * BIT
            lev = 1 if ph < (T1 if bits[k] else T0) else 0
        n += 1
        if lev != v:
            e += 1
    return e, n


def fit_capture(samples, bits, pos_ns, T0, T1, P0=None):
    best = None
    Ps = [2490 + 0.4 * k for k in range(100)] if P0 is None else \
         [P0 + 0.1 * k for k in range(-15, 16)]
    for P in Ps:
        for ti in range(-8, 9):
            t0 = ti * 8.0
            e, n = sample_err(samples, bits, pos_ns, P, t0, 0.0, T0, T1)
            if best is None or e < best[0]:
                best = (e, P, t0, 0.0)
    # refine
    e, P, t0, drift = best
    step = (0.2, 6.0, 0.004)
    for _ in range(60):
        improved = False
        for idx, s in enumerate(step):
            for d in (s, -s):
                cand = [P, t0, drift]
                cand[idx] += d
                e2, _ = sample_err(samples, bits, pos_ns, cand[0], cand[1], cand[2], T0, T1)
                if e2 < e:
                    e, P, t0, drift = e2, cand[0], cand[1], cand[2]
                    improved = True
        if not improved:
            step = tuple(x * 0.5 for x in step)
            if step[0] < 0.01:
                break
    return e, P, t0, drift


def main():
    meta, caps = load_dataset()
    data = []
    for c in caps:
        if c['rep'] == 2:
            continue  # calibrate on train only
        data.append((linearize(c['capture']), frame_bits(c['frame']), c['pattern']))
    pos_ns = [p * 62.5 for p in [1, 5, 9, 13, 17, 21, 27, 32]]
    T0, T1 = 350.0, 700.0
    params = [None] * len(data)
    for outer in range(8):
        tot = 0
        totn = 0
        for j, (s, bits, pat) in enumerate(data):
            P0 = params[j][1] if params[j] else None
            r = fit_capture(s, bits, pos_ns, T0, T1, P0)
            params[j] = r
            tot += r[0]
            e, n = sample_err(s, bits, pos_ns, r[1], r[2], r[3], T0, T1)
            totn += n
        print(f"outer {outer}: err {tot}/{totn} = {tot/totn:.4f}", flush=True)
        # optimize global params
        def gcost(pn, t0v, t1v):
            e = 0
            for j, (s, bits, pat) in enumerate(data):
                _, P, tt0, dr = params[j]
                e += sample_err(s, bits, pn, P, tt0, dr, t0v, t1v)[0]
            return e
        cur = gcost(pos_ns, T0, T1)
        step = 24.0
        while step > 1.0:
            improved = False
            for k in range(8):
                for d in (step, -step):
                    pn = list(pos_ns)
                    pn[k] += d
                    c2 = gcost(pn, T0, T1)
                    if c2 < cur:
                        cur, pos_ns = c2, pn
                        improved = True
            for d in (step, -step):
                c2 = gcost(pos_ns, T0 + d, T1)
                if c2 < cur:
                    cur, T0 = c2, T0 + d
                    improved = True
                c2 = gcost(pos_ns, T0, T1 + d)
                if c2 < cur:
                    cur, T1 = c2, T1 + d
                    improved = True
            if not improved:
                step *= 0.5
        print("  pos_ns", [round(x, 1) for x in pos_ns], "T0", round(T0, 1), "T1", round(T1, 1), "cost", cur, flush=True)
    print(json.dumps({'pos_ns': pos_ns, 'T0': T0, 'T1': T1,
                      'per_capture': [(p[1], p[2], p[3]) for p in params]}))


if __name__ == '__main__':
    main()
