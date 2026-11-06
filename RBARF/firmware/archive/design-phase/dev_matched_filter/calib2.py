"""Per-capture calibration: t(i,s) = i*P + o_s. Slots decouple given P."""
import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0
NBITS = 192
FRAME_END = NBITS * BIT


def frame_bits(frame_hex):
    return [int(b) for byte in bytes.fromhex(frame_hex) for b in f"{byte:08b}"]


def build_level(bits):
    """return function t->level via precomputed edges"""
    def lv(t):
        if t < 0 or t >= FRAME_END:
            return 0
        k = int(t * (1.0 / BIT))
        u = t - k * BIT
        return 1 if u < (T1H if bits[k] else T0H) else 0
    return lv


def calibrate(samples, bits, Pgrid, ogrid_step=5.0, quad=(0.0,)):
    lv = build_level(bits)
    # organize samples per slot
    per_slot = [[] for _ in range(8)]
    for it, sl, v in samples:
        per_slot[sl].append((it, v))
    best = None
    for a in quad:
        for P in Pgrid:
            tot = 0
            offs = []
            for s in range(8):
                bo, bs = None, 0.0
                o = 0.0
                while o < P:
                    g = 0
                    for it, v in per_slot[s]:
                        t = it * P + a * it * it + o
                        if t >= FRAME_END + 1500:
                            break
                        if lv(t) == v:
                            g += 1
                        # count only in-frame
                    if bo is None or g > bo:
                        bo, bs = g, o
                    o += ogrid_step
                tot += bo
                offs.append(bs)
            if best is None or tot > best[0]:
                best = (tot, P, a, offs)
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    Pgrid = [2400 + 2.0 * i for i in range(80)]
    results = []
    for c in train:
        s = linearize(c['capture'])
        bits = frame_bits(c['frame'])
        b = calibrate(s, bits, Pgrid, 10.0)
        # refine P
        Pg2 = [b[1] - 2 + 0.2 * i for i in range(21)]
        b = calibrate(s, bits, Pg2, 2.0)
        Pg3 = [b[1] - 0.2 + 0.04 * i for i in range(11)]
        b = calibrate(s, bits, Pg3, 0.5)
        n_in = sum(1 for it, sl, v in s if it * b[1] + b[3][sl] < FRAME_END + 1500)
        results.append((c, b, n_in))
        print(f"{c['pattern']:11s} r{c['rep']} P={b[1]:8.2f} match={b[0]:4d}/{n_in:4d} "
              f"offs={' '.join('%7.1f' % o for o in b[3])}  cyc={' '.join('%5.2f' % (o/b[1]*40.0) for o in b[3])}")
    tot = sum(b[0] for _, b, _ in results)
    totn = sum(n for _, _, n in results)
    print(f"TOTAL {tot}/{totn} = {tot/totn:.3%}")


main()
