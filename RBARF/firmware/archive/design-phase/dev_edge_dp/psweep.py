"""Parallel sweep of decoder configurations (train split)."""
import sys
import os
import importlib.util
import multiprocessing as mp
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

MODPATH = os.environ.get(
    'EDGE_DP_MOD',
    '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp/frozen_base.py')
_CACHE = {}


def _work(cfg):
    spec = importlib.util.spec_from_file_location('frozen_base', MODPATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for k, v in cfg.items():
        setattr(m, k, v)
    meta, caps = load_dataset()
    subset = [c for c in caps if c['rep'] in (0, 1)]
    ex = 0
    bb = 0
    for c in subset:
        d = m.decode(linearize(c['capture']), meta)
        e = bytes.fromhex(c['payload'])
        if d == e:
            ex += 1
        else:
            eb = ''.join(format(x, '08b') for x in e)
            gb = ''.join(format(x, '08b') for x in (d or b'\0' * 16))
            bb += sum(1 for i in range(128) if eb[i] != gb[i])
    return ex, bb, cfg


def main():
    cfgs = eval(sys.argv[1])
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    with mp.Pool(nproc) as pool:
        res = []
        for r in pool.imap_unordered(_work, cfgs):
            res.append(r)
            print('%2d/36  wb=%4d  %s' % r)
            sys.stdout.flush()
    res.sort(key=lambda r: (-r[0], r[1]))
    print('--- best ---')
    for r in res[:12]:
        print('%2d/36  wb=%4d  %s' % r)


if __name__ == '__main__':
    main()
