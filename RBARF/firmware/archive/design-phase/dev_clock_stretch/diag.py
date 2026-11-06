"""Per-bit diagnostics for clock_stretch."""
import sys, importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


def main():
    meta, caps = load_dataset()
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for c in caps:
        if c['rep'] == 2:
            continue
        if only and c['pattern'] != only:
            continue
        s = linearize(c['capture'])
        fbits = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        m = cs._fit_rigid(s)
        nmax = s[-1][0]
        best = (cs._known_score(cs._llr_bits(s, m)), m)
        for _ in range(4):
            corr = cs._pll_correction(s, m, nmax)
            if corr is None:
                break
            m2 = cs._Model(m.cyc, m.t0, m.dr, corr)
            sc = cs._known_score(cs._llr_bits(s, m2))
            if sc > best[0]:
                best = (sc, m2)
            m = m2
        m = best[1]
        llr = cs._llr_bits(s, m)
        errs = []
        for k in range(cs.NBITS):
            dec = 1 if llr[k] > 0 else 0
            if dec != fbits[k]:
                errs.append((k, fbits[k], round(llr[k], 2)))
        hdrerr = [e for e in errs if e[0] < 32]
        trlerr = [e for e in errs if e[0] >= 160]
        pay = [e for e in errs if 32 <= e[0] < 160]
        weak = sum(1 for k in range(32, 160) if abs(llr[k]) < 0.7)
        print(f"{c['pattern']:11s} {c['rep']} cyc={m.cyc:.4f} P={m.cyc*40:8.2f} t0={m.t0:6.1f} dr={m.dr:.5f} "
              f"hdr_err={len(hdrerr)} trl_err={len(trlerr)} pay_err={len(pay)} weak={weak}")
        if pay:
            print("      ", pay[:24])


main()
