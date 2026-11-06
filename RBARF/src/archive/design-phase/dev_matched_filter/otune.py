"""Coordinate descent on the decoder's real objective (train bit errors).

Parameters: the 8 slot offsets, T0H, T1H.  Parallel over captures.
"""
import sys, os, json, importlib.util
from concurrent.futures import ProcessPoolExecutor
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

META, ALLC = load_dataset()
SPLIT = os.environ.get('SPLIT', 'train')
SEL = (0, 1) if SPLIT == 'train' else ((2,) if SPLIT == 'holdout' else (0, 1, 2))
CAPS = [c for c in ALLC if c['rep'] in SEL]


def _work(a):
    idx, over = a
    import importlib.util as iu
    spec = iu.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
    mf = iu.module_from_spec(spec)
    spec.loader.exec_module(mf)
    for k, v in over.items():
        setattr(mf, k, v)
    c = CAPS[idx]
    s = linearize(c['capture'])
    truth = bytes.fromhex(c['payload'])
    got = mf.decode(s, META) or b'\0' * 16
    tb = [int(b) for byte in truth for b in f"{byte:08b}"]
    gb = [int(b) for byte in got for b in f"{byte:08b}"]
    return sum(1 for x, y in zip(tb, gb) if x != y), int(got == truth)


def evaluate(ex, over):
    res = list(ex.map(_work, [(i, over) for i in range(len(CAPS))]))
    return sum(r[0] for r in res), sum(r[1] for r in res)


if __name__ == '__main__':
    spec = importlib.util.spec_from_file_location('mf0', R + '/approaches/matched_filter.py')
    mf0 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mf0)
    O = json.loads(sys.argv[1]) if len(sys.argv) > 1 else list(mf0.SLOT_O)
    t0, t1 = mf0.T0H, mf0.T1H
    nw = int(os.environ.get('NW', '12'))
    with ProcessPoolExecutor(max_workers=nw) as ex:
        cur, ce = evaluate(ex, {'SLOT_O': O, 'T0H': t0, 'T1H': t1,
                                'VARIANTS': [(t0, t1, 60.0, 0.011, 1.0)]})
        print(f"start biterr={cur} exact={ce} O={O} T0={t0} T1={t1}", flush=True)
        for step in (12.0, 6.0, 3.0):
            for rnd in range(3):
                improved = False
                for idx in range(10):
                    for d in (-step, step):
                        O2, a, b = list(O), t0, t1
                        if idx < 8:
                            O2[idx] += d
                        elif idx == 8:
                            a += d
                        else:
                            b += d
                        v, e = evaluate(ex, {'SLOT_O': O2, 'T0H': a, 'T1H': b,
                                             'VARIANTS': [(a, b, 60.0, 0.011, 1.0)]})
                        if v < cur:
                            cur, ce, O, t0, t1 = v, e, O2, a, b
                            improved = True
                            print(f"  -> biterr={cur} exact={ce} idx={idx} d={d:+.1f}",
                                  flush=True)
                print(f"step={step} biterr={cur} exact={ce} "
                      f"O={[round(x,1) for x in O]} T0={t0} T1={t1}", flush=True)
                if not improved:
                    break
    print("FINAL", json.dumps([round(float(x), 2) for x in O]), t0, t1)
