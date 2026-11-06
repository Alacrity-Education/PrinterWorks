import sys, importlib.util, math
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


def run(c, verbose=False):
    s = linearize(c['capture'])
    fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
    cyc = cs._cycles(s)
    br = cs._rises(s, cyc)
    br.insert(0, (cyc[0] - 2.0, cyc[0]))
    best = None
    for rate in (19.4, 19.7, 20.0, 20.3, 20.6):
        ks = cs._assign(br, rate)
        C = cs._fit_curve(ks, br, rate, 0)
        if C is None:
            continue
        llr = cs._decode_llr(s, cyc, C)
        sc = cs._known_score(llr)
        if best is None or sc > best[0]:
            best = (sc, llr, C, ks, rate)
    sc, llr, C, ks, rate = best
    errs = [(k, fb[k], round(llr[k], 2)) for k in range(cs.NBITS)
            if (1 if llr[k] > 0 else 0) != fb[k]]
    hdr = [e for e in errs if e[0] < 32]
    trl = [e for e in errs if e[0] >= 160]
    pay = [e for e in errs if 32 <= e[0] < 160]
    span = [round(C[k + 1] - C[k], 2) for k in range(0, 192, 16)]
    print(f"{c['pattern']:11s}{c['rep']} rate={rate} kmax={ks[-1]} nbr={len(br)} "
          f"hdr={len(hdr)} trl={len(trl)} pay={len(pay)} spans={span}")
    if pay and verbose:
        print("   ", pay[:30])
    if hdr and verbose:
        print("  H:", hdr)
    if trl and verbose:
        print("  T:", trl)
    return len(pay)


meta, caps = load_dataset()
only = sys.argv[1] if len(sys.argv) > 1 else None
tot = 0
for c in caps:
    if c['rep'] == 2:
        continue
    if only and c['pattern'] != only:
        continue
    tot += run(c, verbose=bool(only) or True)
print('total payload bit errors', tot)
