"""Tuning harness: evaluate matched_filter with overridden constants."""
import sys, os, importlib.util, json
from concurrent.futures import ProcessPoolExecutor
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

META, ALLC = load_dataset()
CACHE = {}


def load():
    spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
    mf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mf)
    return mf


def run_one(args):
    over, key = args
    mf = load()
    for k, v in over.items():
        setattr(mf, k, v)
    sel = (0, 1) if key == 'train' else ((2,) if key == 'holdout' else (0, 1, 2))
    nex = 0; nb = 0; n = 0; berr = 0
    detail = []
    for c in ALLC:
        if c['rep'] not in sel:
            continue
        s = linearize(c['capture'])
        truth = bytes.fromhex(c['payload'])
        got = mf.decode(s, META)
        n += 1
        ok = got == truth
        nex += ok
        g = got or b'\0' * 16
        nb += sum(1 for a, b in zip(g, truth) if a == b)
        tb = [int(b) for byte in truth for b in f"{byte:08b}"]
        gb = [int(b) for byte in g for b in f"{byte:08b}"]
        e = sum(1 for a, b in zip(tb, gb) if a != b)
        berr += e
        detail.append((c['pattern'], c['rep'], ok, e))
    return over, nex, n, nb / (16 * n), berr, detail


if __name__ == '__main__':
    cfgs = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else [{}]
    key = sys.argv[2] if len(sys.argv) > 2 else 'train'
    nw = int(os.environ.get('NW', '8'))
    with ProcessPoolExecutor(max_workers=nw) as ex:
        for over, nex, n, ba, berr, detail in ex.map(
                run_one, [(c, key) for c in cfgs]):
            print(f"exact {nex}/{n} byteacc {ba:.3%} biterr {berr}  {json.dumps(over)}",
                  flush=True)
            if os.environ.get('DETAIL'):
                for p, r, ok, e in detail:
                    print(f"    {p:11s} r{r} {'OK' if ok else '  '} {e}")
