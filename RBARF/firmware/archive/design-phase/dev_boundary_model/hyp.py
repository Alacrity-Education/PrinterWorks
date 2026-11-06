"""Is the full-waveform tracking cost discriminative between the decoded
payload hypothesis and the true one?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa


def full_th(th0, bits):
    th = list(th0)
    for k, b in enumerate(bits):
        th[bm.PAY_LO + k] = bm.T1H if b else bm.T0H
    return th


def track_cost(samples, L, B, th):
    res, cost, L2, B2 = bm._track(samples, L, B, th, rounds=3)
    if res is None:
        return None
    loops, S = res
    # raw mismatch count at that trajectory
    pos = {it: S[k] for k, it in enumerate(loops)}
    offs = [L2 * f for f in bm.F]
    bad = 0
    for it, sl, v in samples:
        s = pos.get(it)
        if s is None:
            continue
        t = s + offs[sl]
        if t < 0.0 or t >= bm.FRAME_END:
            pred = 0
        else:
            j = int(t // bm.BIT)
            pred = 1 if (t - j * bm.BIT) < th[j] else 0
        if pred != v:
            bad += 1
    return cost, bad, res, L2, B2


def main():
    meta, caps = load_dataset()
    th0 = bm._thresholds(bytes.fromhex(meta["header"]),
                         bytes.fromhex(meta["trailer"]))
    for c in caps:
        if c["rep"] not in (0, 1):
            continue
        s = linearize(c["capture"])
        dec = bm.decode(s, meta)
        true = bytes.fromhex(c["payload"])
        dbits = bm._bits(dec)
        tbits = bm._bits(true)
        nerr = sum(1 for a, b in zip(dbits, tbits) if a != b)
        cands = bm._seed_candidates(s, th0)
        L0, B0 = cands[0][1], cands[0][2]
        rd = track_cost(s, L0, B0, full_th(th0, dbits))
        rt = track_cost(s, L0, B0, full_th(th0, tbits))
        print(f"{c['pattern']:11s} r{c['rep']} biterr={nerr:3d}  "
              f"decoded cost={rd[0]:7.2f} bad={rd[1]:3d} | "
              f"true cost={rt[0]:7.2f} bad={rt[1]:3d}   "
              f"{'OK' if rt[0] < rd[0] - 1e-9 else ('tie' if abs(rt[0]-rd[0])<1e-9 else 'BAD')}")


if __name__ == "__main__":
    main()
