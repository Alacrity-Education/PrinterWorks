#!/usr/bin/env python3
"""Forensics on the 80 instrumented silicon captures (margin_dumps.json):
1. host-decode parity vs the on-chip verdict (validates dump integrity);
2. per-capture (t0, eps) fit against the calibrated sampler model
   (hypothesis b: t0 spread; thermal eps per code);
3. matched synthetic twin -> decode: weak/tied/cause/delivery real-vs-twin
   (hypothesis c: is the model optimistic at matched operating points?).
Writes dump_analysis.jsonl.
"""
import json
import multiprocessing as mp
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import sweeplib as S  # noqa: E402

FRD = dict(S.FRAMES)
CODE_EPS = {7: 0.0002, 0: -0.0107, 6: 0.0127, 1: -0.0225}


def linearize(raw: bytes):
    n = len(raw)
    out = []
    for i in range(n):
        b = raw[i]
        for k in range(6):
            out.append((i, k, (b >> (5 - k)) & 1))
        if i + 1 < n:
            nb = raw[i + 1]
            out.append((i, 6, (nb >> 7) & 1))
            out.append((i, 7, (nb >> 6) & 1))
    out.sort(key=lambda s: (s[0], s[1]))
    return out


N_FIT_LOOPS = 250            # 480-bit frame = 240 loops


def agree_rate(bits, eps, t0, ref_levels):
    samples, _ = S.simulate(bits, eps, t0, n_iter=N_FIT_LOOPS)
    n = min(len(samples), len(ref_levels))
    return sum(1 for (_, s, a), b in zip(samples[:n], ref_levels[:n])
               if a == b)


def fit_capture(bits, real_levels, eps_seed):
    """Recover (t0, eps) by maximizing raw sample agreement; eps seeded
    from the device's own lock (exact when locked) or the code nominal."""
    ref = real_levels[:N_FIT_LOOPS * 8]

    def agree(ph, eps):
        samples, _ = S.simulate(bits, eps, ph, n_iter=N_FIT_LOOPS)
        return sum(1 for (a, b) in zip((v for _, _, v in samples), ref)
                   if a == b)

    best = (-1, None, None)
    for j in range(-3, 4):                       # eps seed +/- 0.09%
        eps = eps_seed + j * 3e-4
        for ph in range(0, 1201, 25):
            a = agree(float(ph), eps)
            if a > best[0]:
                best = (a, float(ph), eps)
    a0, ph0, eps0 = best
    sp, se = 12.0, 1.5e-4
    while sp > 0.05:
        moved = False
        for dp, de in ((sp, 0.0), (-sp, 0.0), (0.0, se), (0.0, -se),
                       (sp, se), (sp, -se), (-sp, se), (-sp, -se)):
            a = agree(ph0 + dp, eps0 + de)
            if a > a0:
                a0, ph0, eps0 = a, ph0 + dp, eps0 + de
                moved = True
        if not moved:
            sp /= 2.0
            se /= 2.0
    return ph0, eps0, a0 / len(ref)


def merged_loops(samples):
    lut = {(i, s): v for i, s, v in samples}
    return sum(1 for (i, s), v in lut.items()
               if s == 7 and v and lut.get((i + 1, 0)) == 1)


def work(row):
    data = FRD[row["pattern"]]
    bits = S.frame_bits(data)
    raw = bytes.fromhex(row["cap"])
    # 1. host decode of the raw dump
    st, out, info, eps_c = S.decode(raw)
    host_status = ("O" if st == 1 else "C" if st == 2 else
                   f"R{info.cause}")
    host_deliv = st in (1, 2) and out == data
    host_cat = st in (1, 2) and out != data
    # 2. (t0, eps) fit
    lv = [v for _, _, v in linearize(raw)]
    eps_seed = (row["eps_centi"] / 10000.0 if row["eps_centi"] != 0
                else CODE_EPS[row["code"]])
    t0, eps_fit, agree = fit_capture(bits, lv, eps_seed)
    # 3. matched synthetic twin
    tw_samples, _ = S.simulate(bits, eps_fit, t0)
    tw_cap = S.pack(tw_samples)
    st2, out2, info2, _ = S.decode(tw_cap)
    twin_status = ("O" if st2 == 1 else "C" if st2 == 2 else
                   f"R{info2.cause}")
    twin_deliv = st2 in (1, 2) and out2 == data
    real_lin = linearize(raw)
    return {
        "pattern": row["pattern"], "code": row["code"],
        "pass": row["pass"], "t_s": row["t_s"],
        "dev_status": row["status"], "dev_eps_centi": row["eps_centi"],
        "host_status": host_status, "host_delivered": host_deliv,
        "host_catastrophic": host_cat,
        "parity": row["status"] == host_status,
        "n_weak": int(info.n_weak), "n_tied": int(info.n_tied),
        "t0_fit": round(t0, 1), "eps_fit": round(eps_fit, 6),
        "agree": round(agree, 5),
        "twin_status": twin_status, "twin_delivered": twin_deliv,
        "twin_weak": int(info2.n_weak), "twin_tied": int(info2.n_tied),
        "merged_real": merged_loops(real_lin),
        "merged_twin": merged_loops(tw_samples),
    }


def main():
    d = json.load(open(HERE / "margin_dumps.json"))
    rows = d["rows"]
    out = HERE / "dump_analysis.jsonl"
    with mp.Pool(20) as pool, open(out, "w") as f:
        for i, r in enumerate(pool.imap(work, rows)):
            f.write(json.dumps(r) + "\n")
            print(f"{i+1:3d}/{len(rows)} {r['pattern']:13s} code{r['code']} "
                  f"dev={r['dev_status']:3s} host={r['host_status']:3s} "
                  f"parity={'Y' if r['parity'] else 'N'} "
                  f"t0={r['t0_fit']:6.1f} eps={r['eps_fit']*100:+.3f}% "
                  f"agree={r['agree']:.3f} twin={r['twin_status']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
