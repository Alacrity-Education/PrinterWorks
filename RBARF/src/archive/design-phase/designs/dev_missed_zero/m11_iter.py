"""Self-consistent iteration: decode -> refit (t0,k,h0,h1) against the decoded
waveform -> re-decide.  Measures the ceiling of the technique on real data."""
from mz_common import *
import numpy as np
from collections import Counter
from harness import linearize
import m4_decode as M
import m8_v2 as V

HDR = bits_of(HEADER); TRL = bits_of(TRAILER)


def agree(t, bits, h0, h1, lv):
    bn = np.asarray(bits, np.int8)
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < len(bn))
    kc = np.clip(k, 0, len(bn) - 1)
    hi = np.where(bn[kc] == 1, h1, h0)
    return int((((t - k * BIT) < hi) & ok == lv).sum())


def decode_once(recs0, A, lv, k, t0, h0, h1, tol):
    recs = [dict(r) for r in recs0]
    for r in recs:
        for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
            r[kk] = t0 + k * r[kk]
    recs = [r for r in recs if r["rmid"] < NBITS * BIT + 400]
    n = V.index(recs)
    cands = V.decide(recs, n, NBITS, h0=h0, h1=h1, tol=tol)
    bits, soft = V.assemble(recs, n, cands, NBITS)
    return bits, soft, recs, n, cands


def refit(A, lv, bits, k, t0, h0, h1):
    best = (agree(t0 + k * A, bits, h0, h1, lv), t0, k, h0, h1)
    st, sk, sh = 40.0, 8e-5, 20.0
    while st > 0.5:
        found = False
        for dt, dk, dh0, dh1 in ((st, 0, 0, 0), (-st, 0, 0, 0), (0, sk, 0, 0), (0, -sk, 0, 0),
                                 (0, 0, sh, 0), (0, 0, -sh, 0), (0, 0, 0, sh), (0, 0, 0, -sh)):
            c = (best[1] + dt, best[2] + dk, best[3] + dh0, best[4] + dh1)
            a = agree(c[0] + c[1] * A, bits, c[2], c[3], lv)
            if a > best[0]:
                best = (a, *c)
                found = True
        if not found:
            st /= 2; sk /= 2; sh /= 2
    return best[1], best[2], best[3], best[4], best[0]


meta, caps = load()
for NIT in (0, 1, 2, 3):
    for use_hdr in (False, True):
        ok = 0; be = Counter(); pe = Counter(); amb = 0; hard_amb = 0
        for c in caps:
            samples = linearize(c["capture"])
            it, sl, lv, A = V.build(samples)
            recs0 = M.brackets(A, lv)
            k, t0 = V.blind(recs0)
            h0, h1 = 350.0, 700.0
            bits, soft, recs, n, cands = decode_once(recs0, A, lv, k, t0, h0, h1, 120.0)
            for _ in range(NIT):
                b2 = list(bits)
                if use_hdr:
                    b2[:32] = HDR
                    b2[160:192] = TRL
                t0, k, h0, h1, _ = refit(A, lv, b2, k, t0, h0, h1)
                bits, soft, recs, n, cands = decode_once(recs0, A, lv, k, t0, h0, h1, 120.0)
            amb += len(soft)
            # truly hard: fall bracket wider than the 350ns decision window
            for j, r in enumerate(recs):
                u = r["fa"] - n[j] * BIT; v = r["fb"] - n[j] * BIT
                if (v - u) > 350.0:
                    hard_amb += 1
            truth = bits_of(bytes.fromhex(c["frame"]))
            errs = [i for i in range(NBITS) if bits[i] != truth[i]]
            perr = [i for i in errs if 32 <= i < 160]
            payload = M.bits_to_bytes(bits)[4:20]
            ok += (payload == bytes.fromhex(c["payload"]))
            be[len(errs)] += 1; pe[len(perr)] += 1
        print("iters=%d hdr=%d  EXACT %2d/54  biterr %s  payload-biterr %s  amb/cap %.1f hard/cap %.1f"
              % (NIT, use_hdr, ok, dict(sorted(be.items())), dict(sorted(pe.items())),
                 amb / 54, hard_amb / 54))
