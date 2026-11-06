"""Slot-offset calibration via oracle Viterbi residual paths.

With the true bits known the alignment DP collapses to a single hidden state
(the timing residual).  Track the optimal residual path, remove its smooth
(quadratic) component, and average what is left per slot: that is the
systematic slot-offset error.  Iterate.
"""
import sys
import importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

MOD = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp/frozen_base.py'
spec = importlib.util.spec_from_file_location('frozen_base', MOD)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

BIT = M.BIT
NBITS = M.NBITS
INF = M.INF
DT = 20.0
JR = 45
DRIFT = 0.10


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return [(b >> (7 - k)) & 1 for b in fr for k in range(8)]


def viterbi_path(nom, levels, bits):
    n_s = len(nom)
    nj = 2 * JR + 1
    cur = [0.0] * nj
    back = []
    for n in range(n_s):
        row = [INF] * nj
        bp = [-1] * nj
        for j in range(nj):
            t = nom[n] + (j - JR) * DT
            lv = levels[n]
            if t < 0.0 or t >= NBITS * BIT:
                e = 0.0 if lv == 0 else 1.0
            else:
                k = int(t / BIT)
                e = M._emit(t - k * BIT, lv, bits[k])
            if n == 0:
                row[j] = e
                bp[j] = j
            else:
                best = INF
                bj = -1
                for d in (-1, 0, 1):
                    jp = j - d
                    if 0 <= jp < nj and cur[jp] < INF:
                        v = cur[jp] + (DRIFT if d else 0.0)
                        if v < best:
                            best = v
                            bj = jp
                if best < INF:
                    row[j] = best + e
                    bp[j] = bj
        cur = row
        back.append(bp)
    j = min(range(nj), key=lambda x: cur[x])
    cost = cur[j]
    path = [0] * n_s
    for n in range(n_s - 1, -1, -1):
        path[n] = (j - JR) * DT
        j = back[n][j]
    return cost, path


def quadfit(xs, ys):
    n = len(xs)
    sx = sum(xs); sx2 = sum(x * x for x in xs); sx3 = sum(x ** 3 for x in xs)
    sx4 = sum(x ** 4 for x in xs)
    sy = sum(ys); sxy = sum(x * y for x, y in zip(xs, ys))
    sx2y = sum(x * x * y for x, y in zip(xs, ys))
    A = [[n, sx, sx2, sy], [sx, sx2, sx3, sxy], [sx2, sx3, sx4, sx2y]]
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(A[r][i]))
        A[i], A[piv] = A[piv], A[i]
        if abs(A[i][i]) < 1e-12:
            return 0.0, 0.0, 0.0
        for r in range(3):
            if r == i:
                continue
            f = A[r][i] / A[i][i]
            for c in range(i, 4):
                A[r][c] -= f * A[i][c]
    return tuple(A[i][3] / A[i][i] for i in range(3))


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    data = []
    for c in train:
        s = [x for x in linearize(c['capture']) if x[0] <= 100]
        data.append((c, s, frame_bits(c['payload'], meta)))
    slot_off = [M.SLOT_CYCLES[i] / M.LOOP_CYCLES for i in range(8)]   # fraction of P
    for rnd in range(10):
        tot = 0.0
        acc = [[] for _ in range(8)]
        for c, s, bits in data:
            best = None
            plo, phi = M._p_window([(i, sl, v) for i, sl, v in s])
            p = plo
            while p <= phi:
                nom = [p * i + p * slot_off[sl] for i, sl, v in s]
                lv = [v for _, _, v in s]
                cost, path = viterbi_path(nom, lv, bits)
                if best is None or cost < best[0]:
                    best = (cost, p, path)
                p += 0.5
            cost, p, path = best
            tot += cost
            xs = [float(i) for i, _, _ in s]
            r = quadfit(xs, [float(v) for v in path])
            for n, (i, sl, v) in enumerate(s):
                e = path[n] - (r[0] + r[1] * i + r[2] * i * i)
                acc[sl].append(e)
        means = [sum(a) / len(a) if a else 0.0 for a in acc]
        print('round %d cost %.1f  slot resid %s' % (
            rnd, tot, ' '.join('%+6.1f' % x for x in means)))
        print('        cyc %s' % ' '.join('%.3f' % (x * 40) for x in slot_off))
        sys.stdout.flush()
        base = means[0]
        for sidx in range(8):
            slot_off[sidx] += 0.6 * (means[sidx] - base) / 2500.0
    print('FINAL frac', ['%.5f' % x for x in slot_off])
    print('FINAL cyc(L=40)', ['%.3f' % (x * 40) for x in slot_off])


if __name__ == '__main__':
    main()
