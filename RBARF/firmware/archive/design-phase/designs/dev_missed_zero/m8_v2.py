"""Decoder v2: blind Hough grid fit + self-consistent phase refit + decisive-sample
decision with explicit soft outputs.  Ablations selectable from argv.
"""
from mz_common import *
import numpy as np, sys
from collections import Counter
from harness import linearize
import m4_decode as M

H0E, H1E = 350.0, 700.0      # effective wire high durations (refined per capture)
HDR = bits_of(HEADER); TRL = bits_of(TRAILER)


def build(samples):
    it = np.array([i for i, _, _ in samples], float)
    sl = np.array([s for _, s, _ in samples], int)
    lv = np.array([v for _, _, v in samples], bool)
    A = A_of(it, sl, hc_matrix(sl, lv))
    return it, sl, lv, A


def hough(recs, kgrid, t0grid, nbits=NBITS):
    ra = np.array([r["ra"] for r in recs]); rb = np.array([r["rb"] for r in recs])
    rm = (ra + rb) / 2
    best = None
    for k in kgrid:
        Ra, Rb, Rm = k * ra, k * rb, k * rm
        m = Rm < nbits * BIT + 300
        Ra, Rb, Rm = Ra[m], Rb[m], Rm[m]
        if len(Rm) < 20:
            continue
        for t0 in t0grid:
            g = np.round((Rm + t0) / BIT) * BIT
            hit = int((((Ra + t0) <= g) & ((Rb + t0) >= g)).sum())
            resid = float(np.abs(Rm + t0 - g).sum())
            sc = (hit, -resid)
            if best is None or sc > best[0]:
                best = (sc, float(k), float(t0))
    return best


def blind(recs):
    b = hough(recs, np.linspace(0.990, 1.012, 441), np.arange(-300.0, 500.0, 10.0))
    k, t0 = b[1], b[2]
    for _ in range(3):
        b = hough(recs, k + np.linspace(-2e-4, 2e-4, 41), t0 + np.linspace(-12, 12, 25))
        k, t0 = b[1], b[2]
    return k, t0


def index(recs):
    n = [int(round(recs[0]["rmid"] / BIT))]
    for j in range(1, len(recs)):
        n.append(n[-1] + int(round((recs[j]["rmid"] - recs[j - 1]["rmid"]) / BIT)))
    return n


def phase_refit(recs, n):
    """Interval-feasible affine phase correction: t' = t + a + b*(n)."""
    n = np.array(n, float)
    ra = np.array([r["ra"] for r in recs]) - n * BIT
    rb = np.array([r["rb"] for r in recs]) - n * BIT
    best = None
    for b in np.linspace(-3.0, 3.0, 121):        # ns per bit
        lo = ra + b * n; hi = rb + b * n
        # choose a maximizing #{lo <= -a <= hi}  ->  sweep candidate -a at endpoints
        cand = np.concatenate([lo, hi])
        for x in cand:
            hit = int(((lo <= x) & (hi >= x)).sum())
            if best is None or hit > best[0]:
                best = (hit, -x, b)
    return best[1], best[2]      # a (add to t), b (slope per bit index)


def decide(recs, n, nbits, h0=H0E, h1=H1E, tol=0.0):
    """Per pulse: candidate (span,last) sets from the fall bracket."""
    out = []
    for j, r in enumerate(recs):
        nxt = n[j + 1] if j + 1 < len(recs) else nbits
        maxs = max(1, nxt - n[j])
        u = r["fa"] - n[j] * BIT
        v = r["fb"] - n[j] * BIT
        cands = []
        for s in range(1, min(maxs, 4) + 1):
            for bb in (0, 1):
                ht = (s - 1) * BIT + (h1 if bb else h0)
                if ht > u - tol and ht <= v + tol:
                    cands.append((s, bb, abs(ht - (u + v) / 2)))
        if not cands:
            for s in range(1, min(maxs, 4) + 1):
                for bb in (0, 1):
                    ht = (s - 1) * BIT + (h1 if bb else h0)
                    cands.append((s, bb, abs(ht - (u + v) / 2)))
        cands.sort(key=lambda x: x[2])
        out.append(cands)
    return out


def assemble(recs, n, cands, nbits):
    bits = [0] * nbits
    soft = []
    for j, r in enumerate(recs):
        s, bb, _ = cands[j][0]
        nxt = n[j + 1] if j + 1 < len(recs) else nbits
        s = max(1, min(s, nxt - n[j]))
        for a in range(s - 1):
            if 0 <= n[j] + a < nbits:
                bits[n[j] + a] = 1
        if 0 <= n[j] + s - 1 < nbits:
            bits[n[j] + s - 1] = bb
        if len(cands[j]) > 1:
            soft.append((j, n[j], [(c[0], c[1]) for c in cands[j]]))
    return bits, soft


def run(mode, tol, refit):
    meta, caps = load()
    ok = 0; be = Counter(); perr = Counter(); tot_amb = 0
    for c in caps:
        samples = linearize(c["capture"])
        it, sl, lv, A = build(samples)
        recs = M.brackets(A, lv)
        if mode == "gt":
            key = f"{c['pattern']}_{c['rep']}"
            t0, k = CAL["nuis"][key][0], CAL["nuis"][key][1]
        else:
            k, t0 = blind(recs)
        for r in recs:
            for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
                r[kk] = t0 + k * r[kk]
        recs = [r for r in recs if r["rmid"] < NBITS * BIT + 400]
        n = index(recs)
        if refit:
            for _ in range(2):
                a, b = phase_refit(recs, n)
                nn = np.array(n, float)
                for j, r in enumerate(recs):
                    for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
                        r[kk] += a + b * nn[j]
                n = index(recs)
        cands = decide(recs, n, NBITS, tol=tol)
        bits, soft = assemble(recs, n, cands, NBITS)
        tot_amb += len(soft)
        truth = bits_of(bytes.fromhex(c["frame"]))
        errs = [i for i in range(NBITS) if bits[i] != truth[i]]
        pe = [i for i in errs if 32 <= i < 160]
        payload = M.bits_to_bytes(bits)[4:20]
        e = payload == bytes.fromhex(c["payload"])
        ok += e; be[len(errs)] += 1; perr[len(pe)] += 1
    print("mode=%-5s tol=%5.0f refit=%d  EXACT %2d/54  bit-err %s  payload-bit-err %s  amb/cap %.1f"
          % (mode, tol, refit, ok, dict(sorted(be.items())), dict(sorted(perr.items())), tot_amb / 54))


for mode in ("blind", "gt"):
    for refit in (0, 1):
        for tol in (0.0, 60.0, 120.0):
            run(mode, tol, refit)
