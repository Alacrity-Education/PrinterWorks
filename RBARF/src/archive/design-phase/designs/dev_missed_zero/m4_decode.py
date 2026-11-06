"""End-to-end gap-accounting decoder, GT-free (blind rise-bracket grid fit).

Pipeline:
  1. high runs -> rise/fall brackets in model-clock units A
  2. blind (t0,k) fit: every WS2812 bit starts with a rising edge at an exact
     multiple of BIT, so each rise bracket must straddle a grid point.
  3. incremental bit indices from delta-rise / BIT
  4. per-pulse (span,last) from the fall-bracket candidate set
  5. hidden zeros = index advance - span
"""
from mz_common import *
from collections import Counter
import numpy as np, sys

H0, H1 = 350.0, 700.0
CANDS = [((s, bb), (s - 1) * BIT + (H1 if bb else H0)) for s in (1, 2, 3, 4) for bb in (0, 1)]
TOL = 120.0
HEADER_BITS = bits_of(HEADER)
TRAILER_BITS = bits_of(TRAILER)


def brackets(A, lv):
    """-> list of dicts with rise/fall brackets in A-units (model clock)."""
    out = []
    n = len(A)
    for i0, i1 in pulse_runs(lv):
        ra = A[i0 - 1] if i0 > 0 else A[i0] - 250.0
        fb = A[i1 + 1] if i1 + 1 < n else A[i1] + 250.0
        out.append(dict(i0=i0, i1=i1, ra=ra, rb=A[i0], fa=A[i1], fb=fb,
                        rmid=(ra + A[i0]) / 2, fmid=(A[i1] + fb) / 2,
                        ns=i1 - i0 + 1))
    return out


def blind_fit(recs, nbits=NBITS, kgrid=None, t0grid=None):
    """Maximize the number of rise brackets straddling a BIT grid point."""
    ra = np.array([r["ra"] for r in recs])
    rb = np.array([r["rb"] for r in recs])
    rm = np.array([r["rmid"] for r in recs])
    best = None
    if kgrid is None:
        kgrid = np.linspace(0.990, 1.012, 441)
    if t0grid is None:
        t0grid = np.arange(-300.0, 500.0, 10.0)
    for k in kgrid:
        Ra, Rb, Rm = k * ra, k * rb, k * rm
        m = Rm < nbits * BIT + 300
        if m.sum() < 20:
            continue
        Ra, Rb, Rm = Ra[m], Rb[m], Rm[m]
        for t0 in t0grid:
            g = np.round((Rm + t0) / BIT) * BIT
            hit = int((((Ra + t0) <= g + 1e-9) & ((Rb + t0) >= g - 1e-9)).sum())
            resid = float(np.abs(Rm + t0 - g).sum())
            sc = (hit, -resid)
            if best is None or sc > best[0]:
                best = (sc, float(k), float(t0))
    # polish
    k, t0 = best[1], best[2]
    for _ in range(3):
        kg = k + np.linspace(-2e-4, 2e-4, 41)
        tg = t0 + np.linspace(-12, 12, 25)
        b2 = None
        for kk in kg:
            Ra, Rb, Rm = kk * ra, kk * rb, kk * rm
            m = Rm < nbits * BIT + 300
            Ra, Rb, Rm = Ra[m], Rb[m], Rm[m]
            for tt in tg:
                g = np.round((Rm + tt) / BIT) * BIT
                hit = int((((Ra + tt) <= g + 1e-9) & ((Rb + tt) >= g - 1e-9)).sum())
                resid = float(np.abs(Rm + tt - g).sum())
                sc = (hit, -resid)
                if b2 is None or sc > b2[0]:
                    b2 = (sc, float(kk), float(tt))
        best = b2
        k, t0 = best[1], best[2]
    return best[1], best[2], best[0]


def classify(r, n, tol=TOL):
    u = r["fa"] - n * BIT
    v = r["fb"] - n * BIT
    surv = [(kk, ht) for kk, ht in CANDS if (ht > u - tol) and (ht <= v + tol)]
    if not surv:
        surv = CANDS
    mid = (u + v) / 2
    surv.sort(key=lambda x: abs(x[1] - mid))
    return surv


def decode_capture(samples, nbits=NBITS, dbg=None):
    it = np.array([i for i, _, _ in samples], float)
    sl = np.array([s for _, s, _ in samples], int)
    lv = np.array([v for _, _, v in samples], bool)
    Hc = hc_matrix(sl, lv)
    A = A_of(it, sl, Hc)
    recs = brackets(A, lv)
    if len(recs) < 20:
        return None, {}
    k, t0, sc = blind_fit(recs)
    for r in recs:
        for key in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
            r[key] = t0 + k * r[key]
    recs = [r for r in recs if r["rmid"] < nbits * BIT + 400]
    # incremental indices
    n = [0] * len(recs)
    n[0] = int(round(recs[0]["rmid"] / BIT))
    for j in range(1, len(recs)):
        n[j] = n[j - 1] + int(round((recs[j]["rmid"] - recs[j - 1]["rmid"]) / BIT))
    bits = [0] * nbits
    amb = []
    for j, r in enumerate(recs):
        surv = classify(r, n[j])
        (s, lastb), _ = surv[0]
        nxt = n[j + 1] if j + 1 < len(recs) else nbits
        s = max(1, min(s, nxt - n[j]))
        for a in range(s - 1):
            if 0 <= n[j] + a < nbits:
                bits[n[j] + a] = 1
        if 0 <= n[j] + s - 1 < nbits:
            bits[n[j] + s - 1] = lastb
        if len(surv) > 1:
            amb.append((j, n[j], [x[0] for x in surv[:3]]))
    info = dict(k=k, t0=t0, score=sc, npulse=len(recs), namb=len(amb),
                idx=n, recs=recs, bits=bits)
    return bits, info


def bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)


if __name__ == "__main__":
    from harness import linearize
    meta, caps = load()
    ok = 0
    tot = 0
    bit_err = Counter()
    per = []
    for c in caps:
        samples = linearize(c["capture"])
        bits, info = decode_capture(samples)
        truth = bits_of(bytes.fromhex(c["frame"]))
        errs = [i for i in range(NBITS) if bits[i] != truth[i]]
        fb = bits_to_bytes(bits)
        payload = fb[4:20]
        exact = payload == bytes.fromhex(c["payload"])
        hdr_ok = fb[:4] == HEADER and fb[20:24] == TRAILER
        ok += exact
        tot += 1
        bit_err[len(errs)] += 1
        per.append((c["pattern"], c["rep"], len(errs), exact, hdr_ok, info["namb"],
                    info["npulse"], info["k"], info["t0"], errs[:8]))
    for p in per:
        print("%-11s %d biterr=%2d exact=%d hdr=%d amb=%3d np=%3d k=%.5f t0=%6.1f %s"
              % (p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]))
    print("\nEXACT %d/%d  bit-error histogram %s" % (ok, tot, dict(sorted(bit_err.items()))))
