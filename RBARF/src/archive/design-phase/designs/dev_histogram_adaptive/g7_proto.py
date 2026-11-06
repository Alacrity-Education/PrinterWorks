"""End-to-end prototype of histogram_adaptive.

Stages
  S1  receiver coordinate from slot geometry (nominal or calibrated)
  S2  edge extraction -> rise/fall BRACKETS (interval observations)
  S3  comb fit for P0, integer bit indices for rises, interval regression
      of tau(k) = beta + P*k  (+ optional quadratic drift)
  S4  per-capture 2-cluster fit of the fall phases -> h0hat, h1hat, and
      the boundary theta; margin per cell
  S5  hard classification -> bit string
  S6  global constraint repair (192 bits, header, trailer) by cheapest
      flips ranked by margin
  S7  re-fit with the repaired labels (supervised by header+trailer)

Reports exact-match rate after each stage.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
DRIFT = "-nodrift" not in sys.argv
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)

HDRBITS = np.array([(b >> (7 - k)) & 1 for b in HDR for k in range(8)])
TRLBITS = np.array([(b >> (7 - k)) & 1 for b in TRL for k in range(8)])
KNOWN = np.full(192, -1, dtype=np.int8)
KNOWN[:32] = HDRBITS
KNOWN[160:] = TRLBITS


# ---------------------------------------------------------------- S2
def brackets(lv, x):
    ev = edge_list(lv)
    rises, falls = [], []
    if lv[0] == 1:
        rises.append((x[0] - 300.0, x[0]))
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((x[a], x[b]))
    return rises, falls


def pair_cells(rises, falls):
    """cell i: rise i, the first fall after it, next rise (or None)."""
    out = []
    fi = 0
    for i, (ra, rb) in enumerate(rises):
        while fi < len(falls) and falls[fi][1] <= rb:
            fi += 1
        if fi >= len(falls):
            break
        nxt = rises[i + 1] if i + 1 < len(rises) else None
        out.append((ra, rb, falls[fi][0], falls[fi][1], nxt))
    return out


# ---------------------------------------------------------------- S3
def comb(per, lo=1180.0, hi=1330.0, n=6001):
    per = np.asarray(per, float)
    best = None
    for k in range(n):
        P = lo + k * (hi - lo) / (n - 1)
        q = per / P
        s = q <= 4.5
        e = float(np.sum((q[s] - np.round(q[s])) ** 2))
        if best is None or e < best[1]:
            best = (P, e)
    return best[0]


def interval_cost(rmid_lo, rmid_hi, kk, beta, P, gam=0.0):
    """sum of squared excursion of tau(k) outside each rise bracket."""
    tau = beta + P * kk + gam * kk * kk
    lo_ex = np.maximum(rmid_lo - tau, 0.0)
    hi_ex = np.maximum(tau - rmid_hi, 0.0)
    e = lo_ex + hi_ex
    return float(np.sum(e * e))


def fit_tau(ra, rb, kk, P0, drift=True):
    beta = float(np.median(0.5 * (ra + rb) - P0 * kk))
    P, gam = P0, 0.0
    for rnd in range(6):
        sP = 4.0 / (2 ** rnd)
        sB = 60.0 / (2 ** rnd)
        sG = (0.02 / (2 ** rnd)) if drift else 0.0
        cur = interval_cost(ra, rb, kk, beta, P, gam)
        improved = True
        while improved:
            improved = False
            for dB in (-sB, sB):
                v = interval_cost(ra, rb, kk, beta + dB, P, gam)
                if v < cur - 1e-9:
                    cur, beta = v, beta + dB; improved = True
            for dP in (-sP, sP):
                v = interval_cost(ra, rb, kk, beta, P + dP, gam)
                if v < cur - 1e-9:
                    cur, P = v, P + dP; improved = True
            if sG:
                for dG in (-sG, sG):
                    v = interval_cost(ra, rb, kk, beta, P, gam + dG)
                    if v < cur - 1e-9:
                        cur, gam = v, gam + dG; improved = True
    return beta, P, gam


def assign_k(cells, P0, beta0=None):
    """integer bit index of each cell's rise, from cumulative periods."""
    rmid = np.array([0.5 * (c[0] + c[1]) for c in cells])
    n = np.ones(len(cells), dtype=int)
    if len(cells) > 1:
        per = np.diff(rmid)
        n[:-1] = np.maximum(1, np.round(per / P0).astype(int))
    k = np.concatenate([[0], np.cumsum(n)[:-1]])
    return k, n


# ---------------------------------------------------------------- S4
def two_cluster(v, a=0.30, b=0.59, iters=60):
    v = np.asarray(v)
    for _ in range(iters):
        th = 0.5 * (a + b)
        s = v < th
        if s.any(): a = float(np.median(v[s]))
        if (~s).any(): b = float(np.median(v[~s]))
    return a, b


def decode_capture(c, geom=(CAL_O, CAL_G), drift=True, repair=True,
                   verbose=False):
    O, G = geom
    x = coord(c["it"], c["sl"], O, G)
    lv = c["lv"]
    rises, falls = brackets(lv, x)
    cells = pair_cells(rises, falls)
    if len(cells) < 100:
        return None, {}
    ra = np.array([z[0] for z in cells]); rb = np.array([z[1] for z in cells])
    fa = np.array([z[2] for z in cells]); fb = np.array([z[3] for z in cells])
    rmid = 0.5 * (ra + rb)
    P0 = comb(np.diff(rmid))
    info = {}
    for it in range(4):
        kk, ncell = assign_k(cells, P0)
        beta, P, gam = fit_tau(ra, rb, kk.astype(float), P0, drift=drift)
        if abs(P - P0) < 0.05:
            P0 = P
            break
        P0 = P
    kk, ncell = assign_k(cells, P0)
    beta, P, gam = fit_tau(ra, rb, kk.astype(float), P0, drift=drift)

    def tau(k):
        k = np.asarray(k, float)
        return beta + P * k + gam * k * k

    # ---- fall phases (relative to the bit that owns the fall) ----
    # merged prefix: number of whole bits between rise and fall
    mlen = np.maximum(1, np.floor((0.5 * (fa + fb) - tau(kk)) / P).astype(int) + 1)
    base = tau(kk + mlen - 1)
    ph_lo = (fa - base) / P
    ph_hi = (fb - base) / P
    ph = 0.5 * (ph_lo + ph_hi)
    h0, h1 = two_cluster(ph)
    th = 0.5 * (h0 + h1)
    info.update(P=P, beta=beta, gam=gam, h0=h0, h1=h1, th=th,
                ncells=len(cells))

    # ---- margin (ambiguity metric) ----
    # signed distance to the boundary, normalised by the bracket half width
    half = 0.5 * (ph_hi - ph_lo) + 1e-6
    margin = (ph - th) / half
    lastbit = (ph > th).astype(int)

    # ---- assemble bit string ----
    def assemble(ncell, mlen, lastbit, kk):
        bits = []
        for i in range(len(ncell)):
            n = ncell[i]; m = min(mlen[i], n)
            seg = [1] * (m - 1) + [int(lastbit[i])] + [0] * (n - m)
            bits.extend(seg)
        return bits

    ncell = ncell.copy()
    ncell[-1] = max(1, 192 - int(kk[-1]))
    bits = assemble(ncell, mlen, lastbit, kk)
    info["nbits_raw"] = len(bits)
    raw = list(bits)

    if repair:
        bits = repair_bits(bits, ncell, mlen, lastbit, kk, margin, info)
    return bits, info


def repair_bits(bits, ncell, mlen, lastbit, kk, margin, info):
    """S6: enforce 192 bits + header/trailer using cheapest margin flips."""
    order = np.argsort(np.abs(margin))
    bits = list(bits)
    # 1) length: adjust the final cell (free) -- already done
    if len(bits) != 192:
        info["len_bad"] = len(bits)
        if len(bits) > 192:
            bits = bits[:192]
        else:
            bits = bits + [0] * (192 - len(bits))
    # 2) header / trailer: flip cheapest cells whose last bit sits on a
    #    known position and disagrees
    lb = np.copy(lastbit)
    for rnd in range(3):
        bad = [k for k in range(192) if KNOWN[k] >= 0 and bits[k] != KNOWN[k]]
        if not bad:
            break
        info.setdefault("hdr_bad", []).append(len(bad))
        # map bit index -> cell whose last bit is there
        pos = {int(kk[i] + min(mlen[i], ncell[i]) - 1): i
               for i in range(len(ncell))}
        changed = False
        for k in bad:
            i = pos.get(k)
            if i is None:
                continue
            lb[i] ^= 1
            bits[k] = int(lb[i])
            changed = True
        if not changed:
            break
    return bits


def main():
    meta, caps = load_all()
    stats = Counter()
    rows = []
    for c in caps:
        for tag, rep in (("raw", False), ("repaired", True)):
            bits, info = decode_capture(c, geom=(O, G), drift=DRIFT,
                                        repair=rep)
            if bits is None:
                continue
            b = np.array(bits[:192])
            t = np.array(c["bits"])
            nerr = int((b != t).sum())
            hdr_ok = bool((b[:32] == t[:32]).all() and (b[160:] == t[160:]).all())
            pay = bytes(int("".join(map(str, b[32 + 8 * i:40 + 8 * i])), 2)
                        for i in range(16))
            exact = pay == bytes.fromhex(c["payload"])
            stats[(tag, "exact")] += int(exact)
            stats[(tag, "n")] += 1
            stats[(tag, "biterr")] += nerr
            if tag == "repaired":
                rows.append((c["key"], nerr, hdr_ok, info.get("P"),
                             info.get("h0"), info.get("h1"),
                             info.get("nbits_raw"), info.get("ncells")))
    for tag in ("raw", "repaired"):
        n = stats[(tag, "n")]
        print(f"{tag:9s} exact {stats[(tag,'exact')]:3d}/{n}  "
              f"total bit errors {stats[(tag,'biterr')]:5d} "
              f"({stats[(tag,'biterr')]/(192*n):.4f}/bit)")
    print("\nper capture (repaired):")
    for r in sorted(rows, key=lambda r: -r[1]):
        print("  %-14s biterr=%3d hdrok=%d P=%.2f h=(%.3f,%.3f) nbits=%d cells=%d"
              % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))


if __name__ == "__main__":
    main()
