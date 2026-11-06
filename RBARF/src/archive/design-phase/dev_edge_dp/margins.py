"""Inspect per-bit decision margins for right and wrong bits."""
import sys
import importlib.util
import math
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

MODPATH = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp/frozen_base.py'


def load():
    spec = importlib.util.spec_from_file_location('frozen_base', MODPATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def analyse(m, samples, meta):
    forced, pl0 = m._frame_masks(meta)
    plo, phi = m._p_window(samples)
    results = []
    p = plo
    while p <= phi + 1e-9:
        nom, levels = m._nominal(samples, p)
        if len(nom) >= 300:
            r = m._align(nom, levels, forced)
            if r[0] < m.INF:
                results.append((r[0], p, r[1], r[2]))
        p += m.P_COARSE
    results.sort(key=lambda r: r[0])
    seeds = [r[1] for r in results[:m.P_REFINE_N]]
    seen = set(round(r[1], 4) for r in results)
    for p0 in seeds:
        k = -int(m.P_COARSE / m.P_FINE)
        while k <= int(m.P_COARSE / m.P_FINE):
            p = p0 + k * m.P_FINE
            k += 1
            key = round(p, 4)
            if key in seen:
                continue
            seen.add(key)
            nom, levels = m._nominal(samples, p)
            r = m._align(nom, levels, forced)
            if r[0] < m.INF:
                results.append((r[0], p, r[1], r[2]))
    acc, w = m._combine(results, pl0)
    results.sort(key=lambda r: r[0])
    return acc, pl0, results, plo, phi


def main():
    m = load()
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    allright = []
    allwrong = []
    for c in train:
        samples = linearize(c['capture'])
        acc, pl0, results, plo, phi = analyse(m, samples, meta)
        pb = [(b >> (7 - k)) & 1 for b in bytes.fromhex(c['payload']) for k in range(8)]
        wrong = []
        for i in range(128):
            g = 1 if acc[pl0 + i] > 0 else 0
            a = abs(acc[pl0 + i])
            if g != pb[i]:
                wrong.append((i, a))
                allwrong.append(a)
            else:
                allright.append(a)
        bp = results[0][1]
        print('%-11s r%d  P=%8.2f win=[%.1f,%.1f] nP=%d  wrong=%s' % (
            c['pattern'], c['rep'], bp, plo, phi, len(results),
            ['(%d,%.2f)' % x for x in wrong]))
        sys.stdout.flush()
    allright.sort()
    allwrong.sort()
    print('right n=%d  median=%.2f  p10=%.2f' % (
        len(allright), allright[len(allright) // 2], allright[len(allright) // 10]))
    if allwrong:
        print('wrong n=%d  median=%.2f  p90=%.2f' % (
            len(allwrong), allwrong[len(allwrong) // 2], allwrong[9 * len(allwrong) // 10]))
        print('wrong margins:', ['%.2f' % x for x in allwrong])


if __name__ == '__main__':
    main()
