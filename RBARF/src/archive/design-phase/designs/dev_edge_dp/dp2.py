"""edge_dp prototype: (phase, slope) Viterbi over the 192-bit trellis.

Time model (globals from dev_calibration, no per-capture oracle):
    A_m = it*G + o[slot] + Hc_m . w          (data-dependent, computable)
    t_m = kappa * A_m + d                    (kappa, d unknown per capture)

Stage A (blind): kappa0 from the frame-span endpoint constraint --
    first rising edge at wire time 0, last falling edge at
    191*1250 + h1 = TEND, both readable from the raw levels because the
    trailer's last byte is 0xFF and the line idles low outside the frame.

Stage B: Viterbi over bit index j = 0..191 with state (d, v):
    d = phase residual of bit-j start (grid DSTEP ns)
    v = per-bit phase increment  (grid VSTEP ns/bit)  == residual rate
    transition d' = d + v, v' in {v-VSTEP, v, v+VSTEP} with penalty.
Header (32 bits) and trailer (32 bits) are pinned; payload bits free
(optionally biased by an external log-prior).
"""
import json
import sys
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM      # noqa: E402
import final as CF      # noqa: E402

F = json.load(open(CAL / "final.json"))
G, O, W, H1, H0 = F["G"], np.array(F["o"]), np.array(F["w"]), F["h1"], F["h0"]
BIT = 1250.0
NB = 192
HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")
HDR_BITS = np.array([(b >> (7 - j)) & 1 for b in HDR for j in range(8)])
TRL_BITS = np.array([(b >> (7 - j)) & 1 for b in TRL for j in range(8)])
TEND = 191 * BIT + H1                      # last falling edge, wire time

BIG = 1e12


def A_of(c):
    it, sl, lv = c["it"], c["sl"], c["lv"]
    n = len(it)
    Hc = np.zeros((n, 8))
    run = np.zeros(8)
    for m in range(n):
        Hc[m] = run
        run[sl[m]] += lv[m]
    return it * G + O[sl] + Hc @ W


def blind_kappa(A, lv):
    """Endpoint constraint: A-span between first rise and last fall."""
    hi = np.nonzero(lv)[0]
    m0, m1 = hi[0], hi[-1]
    # first rise: between the last low before m0 and m0  (capture is edge
    # triggered so m0 is ~sample 0); last fall: between m1 and m1+1
    a0 = A[m0] if m0 == 0 else 0.5 * (A[m0 - 1] + A[m0])
    a1 = 0.5 * (A[m1] + A[m1 + 1]) if m1 + 1 < len(A) else A[m1]
    return TEND / (a1 - a0), a0, a1


def emissions(A, lv, kappa, dgrid, we, floor, hoff=0.0, sr=0.0, dr=0.0,
              slots=None, wes=None):
    """E[b, j, di] = -log P(observed samples of bit j | b, d=dgrid[di]).

    p_high(u) = floor + (1-2 floor) * sigm((h_b+hoff-u)/we) * [rise term]
    rise term = sigm((u-dr)/sr) when sr>0 (models the leading-edge
    uncertainty; identical for b=0/1 so it only sharpens the PHASE
    estimate, not the bit LLR).
    wes: optional per-slot width array (overrides we); needs `slots`.
    """
    t = kappa * A
    nd = len(dgrid)
    E = np.zeros((2, NB, nd))
    sel = (t > dgrid.min() - BIT) & (t < dgrid.max() + NB * BIT + BIT)
    tt = t[sel]
    vv = lv[sel].astype(float)
    ws = None if wes is None else np.asarray(wes)[slots[sel]]
    for di in range(nd):
        u_abs = tt - dgrid[di]
        j = np.floor(u_abs / BIT).astype(int)
        ok = (j >= 0) & (j < NB)
        jj = j[ok]
        u = u_abs[ok] - jj * BIT
        o = vv[ok]
        wj = we if ws is None else ws[ok]
        rise = 1.0 if sr <= 0 else 1.0 / (1.0 + np.exp(-(u - dr) / sr))
        for b, h in ((0, H0), (1, H1)):
            p = 1.0 / (1.0 + np.exp(-(h + hoff - u) / wj)) * rise
            p = floor + (1 - 2 * floor) * p
            c = -(o * np.log(p) + (1 - o) * np.log(1 - p))
            np.add.at(E[b, :, di], jj, c)
    return E


def viterbi(E, dgrid, vgrid, vpen, dpen0, prior=None, pin=True):
    nd, nv = len(dgrid), len(vgrid)
    dstep = dgrid[1] - dgrid[0]
    # v expressed in units of d-grid steps (must be integral)
    vsteps = np.rint(vgrid / dstep).astype(int)
    cost = np.zeros((nd, nv))
    cost += dpen0(dgrid)[:, None]
    cost += 0.5 * (vgrid / max(vgrid.max(), 1e-9) * 1.0) ** 2 * 0.0
    bt_d = np.zeros((NB, nd, nv), dtype=np.int16)
    bt_v = np.zeros((NB, nd, nv), dtype=np.int8)
    bt_b = np.zeros((NB, nd, nv), dtype=np.int8)
    ar = np.arange(nd)
    for j in range(NB):
        # ---- emission / bit decision ----
        if pin and j < 32:
            b = int(HDR_BITS[j]); ec = E[b, j]; eb = np.full(nd, b, np.int8)
        elif pin and j >= 160:
            b = int(TRL_BITS[j - 160]); ec = E[b, j]; eb = np.full(nd, b, np.int8)
        else:
            e0, e1 = E[0, j].copy(), E[1, j].copy()
            if prior is not None:
                e0 = e0 + prior[j, 0]
                e1 = e1 + prior[j, 1]
            eb = (e1 < e0).astype(np.int8)
            ec = np.minimum(e0, e1)
        # ---- transition: d' = d + v, v' in {v-1,v,v+1} ----
        best = np.full((nd, nv), BIG)
        bd = np.zeros((nd, nv), dtype=np.int16)
        bv = np.zeros((nd, nv), dtype=np.int8)
        for vi in range(nv):
            sh = vsteps[vi]
            for dv in (-1, 0, 1):
                vs = vi + dv
                if not (0 <= vs < nv):
                    continue
                src = cost[:, vs]
                # d' index = d index + sh  ->  gather from d'-sh
                dst = np.full(nd, BIG)
                if sh >= 0:
                    if sh < nd:
                        dst[sh:] = src[:nd - sh]
                else:
                    if -sh < nd:
                        dst[:nd + sh] = src[-sh:]
                cand = dst + (vpen if dv else 0.0)
                m = cand < best[:, vi]
                best[m, vi] = cand[m]
                bd[m, vi] = (ar[m] - sh).astype(np.int16)
                bv[m, vi] = vs
        cost = best + ec[:, None]
        bt_d[j] = bd
        bt_v[j] = bv
        bt_b[j] = eb[:, None]
    fi = np.unravel_index(np.argmin(cost), cost.shape)
    total = float(cost[fi])
    bits = np.zeros(NB, dtype=np.int8)
    dtrack = np.zeros(NB)
    di, vi = int(fi[0]), int(fi[1])
    for j in range(NB - 1, -1, -1):
        bits[j] = bt_b[j, di, vi]
        dtrack[j] = dgrid[di]
        di, vi = int(bt_d[j, di, vi]), int(bt_v[j, di, vi])
        di = min(max(di, 0), len(dgrid) - 1)
    return total, bits, dtrack, cost


def bits_to_payload(bits):
    out = bytearray()
    for by in range(4, 20):
        v = 0
        for j in range(8):
            v = (v << 1) | int(bits[by * 8 + j])
        out.append(v)
    return bytes(out)


DEF = dict(dlo=-150.0, dhi=850.0, dstep=12.5, vmax=25.0, vstep=6.25,
           we=45.0, floor=0.01, vpen=1.2, kgrid=(0.0,), d0sig=400.0,
           hoff=0.0, sr=0.0, dr=0.0, wes=None)


def run_capture(c, A=None, prior=None, verbose=False, **kw):
    p = dict(DEF); p.update(kw)
    if A is None:
        A = A_of(c)
    lv = c["lv"]
    k0, a0, a1 = blind_kappa(A, lv)
    dgrid = np.arange(p["dlo"], p["dhi"] + 1e-9, p["dstep"])
    vgrid = np.arange(-p["vmax"], p["vmax"] + 1e-9, p["vstep"])
    d0 = -k0 * a0                      # phase that puts the first rise at 0
    best = None
    for dk in p["kgrid"]:
        kap = k0 * (1.0 + dk)
        E = emissions(A, lv, kap, dgrid, p["we"], p["floor"],
                      hoff=p["hoff"], sr=p["sr"], dr=p["dr"],
                      slots=c["sl"], wes=p["wes"])
        pen = lambda d, d0=d0, s=p["d0sig"]: 0.5 * ((d - d0) / s) ** 2
        tot, bits, dtr, _ = viterbi(E, dgrid, vgrid, p["vpen"], pen, prior)
        if best is None or tot < best[0]:
            best = (tot, bits, dtr, kap)
    return best + (k0,)
