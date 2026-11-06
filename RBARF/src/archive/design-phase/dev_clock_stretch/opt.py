"""Coordinate-descent calibration of the decoder's global constants.

Objective = number of wrong *known* bits (header+trailer) over the train
split, tie-broken by the soft known-bit score.  Payload truth is only
printed for monitoring, never optimised against.
"""
import importlib.util, sys, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize, score

meta, caps = load_dataset()
TRAIN = [(c, linearize(c['capture'])) for c in caps if c['rep'] in (0, 1)]


def fresh():
    spec = importlib.util.spec_from_file_location(
        'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    return cs


def evaluate(params, verbose=False):
    cs = fresh()
    cs.SLOT_POS = list(params['pos'])
    cs.T0H = params['T0H']
    cs.T1H = params['T1H']
    cs.SIG = params['SIG']
    cs.SIG_RISE = params['SIG_RISE']
    cs._rebuild()
    kerr = 0
    ksoft = 0.0
    ex = 0
    acc = 0.0
    perr = 0
    for c, s in TRAIN:
        fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        r = cs._solve(s)
        llr = r[1]
        for k, b in cs.KNOWN.items():
            if (1 if llr[k] > 0 else 0) != b:
                kerr += 1
        for k in range(32, 160):
            if (1 if llr[k] > 0 else 0) != fb[k]:
                perr += 1
        ksoft += r[0]
        out = bytearray()
        for i in range(16):
            v = 0
            for j in range(8):
                v = (v << 1) | (1 if llr[32 + i * 8 + j] > 0 else 0)
            out.append(v)
        e, a = score(bytes(out), bytes.fromhex(c['payload']))
        ex += e
        acc += a
    if verbose:
        print(f"   perr={perr} kerr={kerr} exact={ex}/36 acc={acc/36:.3%}")
    return (perr + kerr,), ex, acc / 36


def main():
    params = {'pos': [1.41, 4.78, 9.88, 12.69, 19.06, 21.97, 27.50, 31.44],
              'T0H': 350.0, 'T1H': 700.0, 'SIG': 70.0, 'SIG_RISE': 55.0}
    cur, ex, acc = evaluate(params, True)
    print('start', cur, ex, acc, flush=True)
    for step in (0.6, 0.3, 0.15, 0.07):
        improved = True
        while improved:
            improved = False
            for k in range(1, 8):
                for d in (step, -step):
                    p2 = {**params, 'pos': list(params['pos'])}
                    p2['pos'][k] += d
                    ok = all(p2['pos'][i] < p2['pos'][i + 1] - 1.0 for i in range(7)) \
                        and p2['pos'][7] < 39.0
                    if not ok:
                        continue
                    v, ex2, acc2 = evaluate(p2)
                    if v < cur:
                        cur, params = v, p2
                        improved = True
                        print(f"  pos[{k}] {d:+.2f} -> {cur} ex={ex2} acc={acc2:.3%} "
                              f"pos={[round(x,2) for x in params['pos']]}", flush=True)
    for name, steps in (('T0H', (20.0, 8.0)), ('T1H', (20.0, 8.0)),
                        ('SIG', (15.0, 6.0)), ('SIG_RISE', (15.0, 6.0))):
        for step in steps:
            improved = True
            while improved:
                improved = False
                for d in (step, -step):
                    p2 = {**params, 'pos': list(params['pos'])}
                    p2[name] += d
                    if p2[name] < 10.0:
                        continue
                    v, ex2, acc2 = evaluate(p2)
                    if v < cur:
                        cur, params = v, p2
                        improved = True
                        print(f"  {name} {d:+.1f} -> {cur} ex={ex2} acc={acc2:.3%}", flush=True)
    print(json.dumps({k: v for k, v in params.items()}))
    evaluate(params, True)


main()
