import sys, importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

meta, caps = load_dataset()
only = sys.argv[1] if len(sys.argv) > 1 else None
rep = int(sys.argv[2]) if len(sys.argv) > 2 else None
tot = 0
for c in caps:
    if c['rep'] == 2:
        continue
    if only and c['pattern'] != only:
        continue
    if rep is not None and c['rep'] != rep:
        continue
    s = linearize(c['capture'])
    fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
    sc, llr, C, rate = cs._solve(s)
    errs = [(k, fb[k], round(llr[k], 2)) for k in range(cs.NBITS)
            if (1 if llr[k] > 0 else 0) != fb[k]]
    hdr = [e for e in errs if e[0] < 32]
    trl = [e for e in errs if e[0] >= 160]
    pay = [e for e in errs if 32 <= e[0] < 160]
    tot += len(pay)
    w = [round(C[k + 1] - C[k], 2) for k in range(0, 192, 12)]
    print(f"{c['pattern']:11s}{c['rep']} rate={rate} sc={sc:7.1f} hdr={len(hdr)} trl={len(trl)} pay={len(pay)}  w={w}")
    if pay:
        print("     P:", pay[:26])
    if hdr:
        print("     H:", hdr[:20])
    if trl:
        print("     T:", trl[:20])
print('TOTAL payload bit errors', tot)
