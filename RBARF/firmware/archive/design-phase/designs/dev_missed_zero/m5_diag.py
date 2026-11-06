"""Diagnose m4 errors: time-base source, error taxonomy."""
import numpy as np, sys
from collections import Counter
from mz_common import *
import m4_decode as M
from harness import linearize

meta, caps = load()
MODE = sys.argv[1] if len(sys.argv) > 1 else "blind"


def run(mode):
    ok = 0
    taxo = Counter()
    biterr = Counter()
    dets = []
    for c in caps:
        samples = linearize(c["capture"])
        it = np.array([i for i, _, _ in samples], float)
        sl = np.array([s for _, s, _ in samples], int)
        lv = np.array([v for _, _, v in samples], bool)
        A = A_of(it, sl, hc_matrix(sl, lv))
        recs = M.brackets(A, lv)
        if mode == "gt":
            key = f"{c['pattern']}_{c['rep']}"
            t0, k = CAL["nuis"][key][0], CAL["nuis"][key][1]
        else:
            k, t0, _ = M.blind_fit(recs)
        for r in recs:
            for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
                r[kk] = t0 + k * r[kk]
        recs = [r for r in recs if r["rmid"] < NBITS * BIT + 400]
        n = [0] * len(recs)
        n[0] = int(round(recs[0]["rmid"] / BIT))
        for j in range(1, len(recs)):
            n[j] = n[j - 1] + int(round((recs[j]["rmid"] - recs[j - 1]["rmid"]) / BIT))
        truth = bits_of(bytes.fromhex(c["frame"]))
        bits = [0] * NBITS
        for j, r in enumerate(recs):
            surv = M.classify(r, n[j])
            (s, lastb), _ = surv[0]
            nxt = n[j + 1] if j + 1 < len(recs) else NBITS
            s = max(1, min(s, nxt - n[j]))
            for a in range(s - 1):
                if 0 <= n[j] + a < NBITS:
                    bits[n[j] + a] = 1
            if 0 <= n[j] + s - 1 < NBITS:
                bits[n[j] + s - 1] = lastb
            # taxonomy: true span for this pulse = 1 + #following bits that are 1
            #           and covered (approx: next pulse start - n[j] gives the
            #           max; truth says bits n..nxt-1)
            true_seg = truth[n[j]:nxt] if 0 <= n[j] < NBITS else []
            got_seg = bits[n[j]:nxt] if 0 <= n[j] < NBITS else []
            if list(true_seg) != list(got_seg):
                # which kind?
                ts = 1
                while ts < len(true_seg) and true_seg[ts - 1] == 1:
                    ts += 1
                if s != ts:
                    taxo["span"] += 1
                elif len(true_seg) and true_seg[s - 1] != lastb:
                    taxo["lastbit"] += 1
                else:
                    taxo["hidden"] += 1
                taxo["_amb" + ("Y" if len(surv) > 1 else "N")] += 1
        errs = [i for i in range(NBITS) if bits[i] != truth[i]]
        payload = M.bits_to_bytes(bits)[4:20]
        e = payload == bytes.fromhex(c["payload"])
        ok += e
        biterr[len(errs)] += 1
        dets.append((c["pattern"], c["rep"], len(errs), e, errs))
    print(f"mode={mode}  EXACT {ok}/{len(caps)}  biterr {dict(sorted(biterr.items()))}")
    print("  error taxonomy:", dict(taxo))
    # error position histogram
    pos = Counter()
    for d in dets:
        for i in d[4]:
            pos[i // 8] += 1
    print("  errors by byte index:", dict(sorted(pos.items())))
    return dets


run("gt")
run("blind")
