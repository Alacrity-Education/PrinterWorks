"""Compare header/trailer-only calibration against a ground-truth
full-frame calibration, and report where bits are lost."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa: E402
import boundary_model as bm  # noqa: E402

BIT, T0H, T1H, NB = bm.BIT, bm.T0H, bm.T1H, bm.NBITS
END = NB * BIT


def full_highs(frame):
    bits = bm._bits(frame)
    return [(i * BIT, i * BIT + (T1H if v else T0H)) for i, v in enumerate(bits)]


def fit_full(samples, frame, F=None):
    F = F or bm.F
    highs = full_highs(frame)
    known = [(0.0, END), (END, 300000.0)]
    xs, vs = [], []
    for it, sl, v in samples:
        if it > 115:
            break
        xs.append(it + F[sl])
        vs.append(v)
    old = bm.F
    bm.F = F

    def scan(lo, hi, step):
        best = (-1, 0.0, 0.0)
        L = lo
        while L <= hi + 1e-9:
            sc, B = bm._best_B(xs, vs, L, highs, known, bm.B_LO, bm.B_HI)
            if sc > best[0]:
                best = (sc, L, B)
            L += step
        return best
    sc, L, B = scan(bm.L_LO, bm.L_HI, 0.3)
    sc, L, B = scan(L - 0.6, L + 0.6, 0.02)
    bm.F = old
    return L, B, sc, len(xs)


def main():
    meta, caps = load_dataset()
    header = bytes.fromhex(meta["header"])
    trailer = bytes.fromhex(meta["trailer"])
    pats = sys.argv[1:] or None
    for c in caps:
        if c["rep"] not in (0, 1):
            continue
        if pats and c["pattern"] not in pats:
            continue
        s = linearize(c["capture"])
        frame = bytes.fromhex(c["frame"])
        Lh, Bh, sch = bm.calibrate(s, header, trailer)
        Lf, Bf, scf, nx = fit_full(s, frame)
        # bits correct with the truth-fitted timebase
        exp = bm._bits(frame)
        def bits_from(L, B):
            cells = bm._cell_samples(s, L, B)
            got, amb = [], 0
            for i in range(NB):
                b, m = bm._classify(cells.get(i, []))
                if b is None:
                    amb += 1
                    b = 1 if any(v for _p, v in cells.get(i, [])) else 0
                got.append(b)
            return got, amb
        gh, ah = bits_from(Lh, Bh)
        gf, af = bits_from(Lf, Bf)
        eh = sum(1 for i in range(32, 160) if gh[i] != exp[i])
        ef = sum(1 for i in range(32, 160) if gf[i] != exp[i])
        print(f"{c['pattern']:11s} r{c['rep']} "
              f"hdrfit L={Lh:8.2f} B={Bh:7.1f} sc={sch}/{nx}  err={eh:3d} amb={ah:3d} | "
              f"fullfit L={Lf:8.2f} B={Bf:7.1f} sc={scf}  err={ef:3d} amb={af:3d}")


if __name__ == "__main__":
    main()
