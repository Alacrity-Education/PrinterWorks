"""Calibrate the sampling-time model against known header/trailer bits."""
import sys, json, math
from pathlib import Path
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return [(b >> (7 - k)) & 1 for b in fr for k in range(8)]


KNOWN = set(range(0, 32)) | set(range(160, 192))


def mismatches(samples, bits, P, t0, g, use=None, maxi=200):
    """count mismatches on bits in `use` (set of bit idx)."""
    bad = 0
    tot = 0
    for (i, s, v) in samples:
        if i > maxi:
            break
        t = t0 + P * (i + g[s])
        if t < -100:
            continue
        k = int(t // BIT)
        if k >= NB:
            exp = 0
            if use is not None and 'tail' not in use:
                continue
        else:
            if use is not None and k not in use:
                continue
            th = 700.0 if bits[k] else 350.0
            exp = 1 if (t - k * BIT) < th else 0
        tot += 1
        if exp != v:
            bad += 1
    return bad, tot


def main():
    meta, caps = load_dataset()
    g0 = [p / 37.0 for p in meta['sample_cycle_positions']]
    print('initial g', ['%.4f' % x for x in g0])
    train = [c for c in caps if c['rep'] in (0, 1)]
    for c in train[:4]:
        samples = linearize(c['capture'])
        bits = frame_bits(c['payload'], meta)
        best = None
        for Pi in range(24800, 25400):
            P = Pi / 10.0
            for t0i in range(0, 140, 10):
                b, t = mismatches(samples, bits, P, float(t0i), g0, use=KNOWN)
                if best is None or b < best[0]:
                    best = (b, t, P, t0i)
        print(c['pattern'], c['rep'], 'bad=%d/%d P=%.1f t0=%d' % best)


if __name__ == '__main__':
    main()
