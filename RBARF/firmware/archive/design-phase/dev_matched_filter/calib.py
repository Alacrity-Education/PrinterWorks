"""Offline calibration of global slot fractions using known frames."""
import sys, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0


def frame_bits(frame_hex):
    return [int(b) for byte in bytes.fromhex(frame_hex) for b in f"{byte:08b}"]


def level_at(bits, t):
    """transmitter level at time t (ns), frame starts at t=0."""
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    u = t - k * BIT
    return 1 if u < (T1H if bits[k] else T0H) else 0


def score(samples, bits, P, g, delta, nmax=None):
    good = 0
    tot = 0
    for it, sl, v in samples:
        t = P * (it + g[sl]) + delta
        if t > len(bits) * BIT + 2000:
            break
        tot += 1
        if level_at(bits, t) == v:
            good += 1
    return good, tot


def fit_capture(samples, bits, g, Prange, drange):
    best = None
    for P in Prange:
        for d in drange:
            gd, tot = score(samples, bits, P, g, d)
            if best is None or gd > best[0]:
                best = (gd, tot, P, d)
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    g = [p / 40.1 for p in [1, 5, 9, 13, 17, 21, 27, 32]]
    g = [x - g[0] for x in g]

    def refine_all(g, coarse=True):
        res = []
        for c in train:
            s = linearize(c['capture'])
            bits = frame_bits(c['frame'])
            Pr = [2490 + 0.5 * i for i in range(80)]
            dr = [-40 + 8 * i for i in range(15)]
            b = fit_capture(s, bits, g, Pr, dr)
            # refine
            Pr = [b[2] - 0.6 + 0.05 * i for i in range(25)]
            dr = [b[3] - 10 + 1.0 * i for i in range(21)]
            b = fit_capture(s, bits, g, Pr, dr)
            res.append((c, s, bits, b))
        return res

    res = refine_all(g)
    tot_good = sum(b[0] for _, _, _, b in res)
    tot_all = sum(b[1] for _, _, _, b in res)
    print(f"init g={['%.4f'%x for x in g]}  match {tot_good}/{tot_all} = {tot_good/tot_all:.4%}")

    # coordinate descent on g[1..7]
    for it in range(6):
        improved = False
        for sl in range(1, 8):
            base = g[sl]
            cands = [base + d for d in (-0.02, -0.01, -0.005, -0.002, 0, 0.002, 0.005, 0.01, 0.02)]
            bestv, bestg = None, base
            for cv in cands:
                g2 = list(g); g2[sl] = cv
                tg = sum(score(s, bits, b[2], g2, b[3])[0] for _, s, bits, b in res)
                if bestv is None or tg > bestv:
                    bestv, bestg = tg, cv
            if bestg != base:
                g[sl] = bestg
                improved = True
        res = refine_all(g)
        tot_good = sum(b[0] for _, _, _, b in res)
        print(f"round {it}: g={['%.4f'%x for x in g]} match {tot_good}/{tot_all} = {tot_good/tot_all:.4%}")
        if not improved:
            break

    print("P per capture:")
    for c, s, bits, b in res:
        print(f"  {c['pattern']:11s} r{c['rep']} P={b[2]:.2f} d={b[3]:.1f} {b[0]}/{b[1]} miss={b[1]-b[0]}")
    json.dump({'g': g}, open('/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_matched_filter/g.json', 'w'))


main()
