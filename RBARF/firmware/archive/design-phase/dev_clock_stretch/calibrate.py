"""Coordinate-descent calibration of the sampler geometry + edge model.

Objective: payload bit errors on the train split (36 captures x 128 bits).
These are 11 hardware/global constants fitted to 4608 labelled bits, and
the holdout split is only looked at at the very end.
"""
import importlib.util, sys, json, time
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize, score

meta, caps = load_dataset()
TRAIN = []
for c in caps:
    if c['rep'] in (0, 1):
        TRAIN.append((linearize(c['capture']),
                      [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"],
                      bytes.fromhex(c['payload'])))

SRC = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py'


def evaluate(params):
    spec = importlib.util.spec_from_file_location('cs', SRC)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    cs.SLOT_POS = list(params['pos'])
    cs.T0H = params['T0H']
    cs.T1H = params['T1H']
    cs.SIG = params['SIG']
    cs.SIG_RISE = params['SIG_RISE']
    cs._rebuild()
    perr = 0
    ex = 0
    for s, fb, pay in TRAIN:
        llr = cs._solve(s)[1]
        for k in range(32, 160):
            if (1 if llr[k] > 0 else 0) != fb[k]:
                perr += 1
        out = bytearray()
        for i in range(16):
            v = 0
            for j in range(8):
                v = (v << 1) | (1 if llr[32 + i * 8 + j] > 0 else 0)
            out.append(v)
        ex += (bytes(out) == pay)
    return perr, ex


def main():
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {
        'pos': [1.41, 4.78, 9.88, 12.69, 19.06, 21.97, 27.50, 31.44],
        'T0H': 350.0, 'T1H': 700.0, 'SIG': 70.0, 'SIG_RISE': 55.0}
    cur, ex = evaluate(params)
    print('start perr', cur, 'exact', ex, flush=True)
    knobs = [('pos', i) for i in range(1, 8)] + \
            [('T0H', None), ('T1H', None), ('SIG', None), ('SIG_RISE', None)]
    for rnd, scale in enumerate((1.0, 0.5, 0.25)):
        for name, idx in knobs:
            step = (0.5 * scale) if name == 'pos' else (25.0 * scale)
            for d in (step, -step, 2 * step, -2 * step):
                p2 = {**params, 'pos': list(params['pos'])}
                if idx is None:
                    p2[name] += d
                    if p2[name] < 15.0 or p2[name] > 900.0:
                        continue
                else:
                    p2['pos'][idx] += d
                    if any(p2['pos'][i] >= p2['pos'][i + 1] - 0.8 for i in range(7)):
                        continue
                    if p2['pos'][7] > 39.0:
                        continue
                t0 = time.time()
                v, ex2 = evaluate(p2)
                if v < cur:
                    cur, params = v, p2
                    print(f"  r{rnd} {name}{idx} {d:+.2f} -> perr={cur} exact={ex2} "
                          f"({time.time()-t0:.0f}s) {json.dumps(params)}", flush=True)
                    break
    print('FINAL', json.dumps(params), 'perr', cur, flush=True)


main()
