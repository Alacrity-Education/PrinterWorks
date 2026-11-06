"""Dev driver: evaluate edge_dp on the train split with parameter overrides."""
import sys
import importlib.util
import time
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

MODPATH = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/edge_dp.py'


def load():
    spec = importlib.util.spec_from_file_location('edge_dp_dev', MODPATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(overrides=None, split=(0, 1), verbose=True, patterns=None):
    m = load()
    for k, v in (overrides or {}).items():
        setattr(m, k, v)
    meta, caps = load_dataset()
    subset = [c for c in caps if c['rep'] in split and
              (patterns is None or c['pattern'] in patterns)]
    ex = 0
    bad_bits = 0
    t0 = time.time()
    for c in subset:
        s = linearize(c['capture'])
        d = m.decode(s, meta)
        expd = bytes.fromhex(c['payload'])
        if d == expd:
            ex += 1
            if verbose:
                print('  ok  %-11s r%d' % (c['pattern'], c['rep']))
        else:
            eb = ''.join(f'{b:08b}' for b in expd)
            gb = ''.join(f'{b:08b}' for b in (d or b'\0' * 16))
            wrong = [i for i in range(128) if eb[i] != gb[i]]
            bad_bits += len(wrong)
            if verbose:
                print('  BAD %-11s r%d  bits %s' % (c['pattern'], c['rep'], wrong))
    print('exact %d/%d  wrongbits=%d  (%.1fs)' % (ex, len(subset), bad_bits, time.time() - t0))
    return ex, len(subset), bad_bits


if __name__ == '__main__':
    run()
