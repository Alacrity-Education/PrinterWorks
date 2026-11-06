"""Diagnostics for approaches/matched_filter.py against ground truth."""
import sys, importlib.util
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

meta, allc = load_dataset()
split = sys.argv[1] if len(sys.argv) > 1 else 'train'
sel = (0, 1) if split == 'train' else ((2,) if split == 'holdout' else (0, 1, 2))
tot_bit_err = 0
nex = 0
n = 0
for c in allc:
    if c['rep'] not in sel:
        continue
    s = linearize(c['capture'])
    truth = bytes.fromhex(c['payload'])
    got = mf.decode(s, meta)
    tb = [int(b) for byte in truth for b in f"{byte:08b}"]
    gb = [int(b) for byte in (got or b'\0' * 16) for b in f"{byte:08b}"]
    errs = [i for i, (a, b) in enumerate(zip(tb, gb)) if a != b]
    tot_bit_err += len(errs)
    n += 1
    ok = got == truth
    nex += ok
    print(f"{c['pattern']:11s} r{c['rep']} {'OK ' if ok else '   '} biterr={len(errs):3d} "
          f"at={errs[:14]}")
print(f"exact {nex}/{n}  total bit errors {tot_bit_err}/{n*128}")
