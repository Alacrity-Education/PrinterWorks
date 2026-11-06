"""Bit-level error report for the current decoder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa


def main():
    meta, caps = load_dataset()
    reps = (0, 1) if "--holdout" not in sys.argv else (2,)
    tot_err = tot_amb = 0
    for c in caps:
        if c["rep"] not in reps:
            continue
        s = linearize(c["capture"])
        exp = bm._bits(bytes.fromhex(c["payload"]))
        th = bm._thresholds(bytes.fromhex(meta["header"]),
                            bytes.fromhex(meta["trailer"]))
        cands = bm._seed_candidates(s, th)
        best = None
        for _sc, L, B in cands:
            res, cost, L2, B2 = bm._track(s, L, B, th)
            if res is None:
                continue
            if best is None or cost < best[0]:
                best = (cost, res, L2)
        cost, (loops, S), L = best
        cells = bm._cells_from(s, loops, S, L)
        errs, ambs, amberr = [], 0, 0
        for k in range(128):
            j = bm.PAY_LO + k
            ph = cells.get(j, [])
            b = bm._classify(ph)
            if b is None:
                ambs += 1
                b = 1 if any(v for _p, v in ph) else 0
                if b != exp[k]:
                    amberr += 1
            if b != exp[k]:
                errs.append(k)
        tot_err += len(errs)
        tot_amb += ambs
        print(f"{c['pattern']:11s} r{c['rep']} cost={cost:7.2f} L={L:8.2f} "
              f"errs={len(errs):3d} (amb={ambs:2d}, amberr={amberr}) {errs[:14]}")
    print(f"TOTAL bit errors {tot_err}  ambiguous {tot_amb}")


if __name__ == "__main__":
    main()
