"""Envelope test of the gap-accounting core on synthetic captures (+/-8% HSI).

Uses the SYNTH slot geometry (nominal cycles) since synthetic captures come
from that model; the blind scale search is widened to cover +/-10%.
Reports the three gap-accounting quantities separately from the last-bit call:
  A) index advance round(dRise/BIT) exact?
  B) span (merge multiplicity) exact?
  C) hidden-zero count exact?
  D) last-bit decision exact?
"""
import sys
from pathlib import Path
import numpy as np
from collections import Counter

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON))
sys.path.insert(0, str(RECON.parent / "bench"))
from synth import synth_capture, SLOT_POS_CY, LOOP_CY, CY_NS  # noqa: E402
from patterns import PATTERNS, frame  # noqa: E402

BIT = 1250.0
H0, H1 = 350.0, 700.0
NBITS = 192
OFFS = np.array([p * CY_NS for p in SLOT_POS_CY])
G = LOOP_CY * CY_NS


def bits_of(fb):
    return [(b >> (7 - k)) & 1 for b in fb for k in range(8)]


def runs_of(lv):
    out = []
    n = len(lv)
    i = 0
    while i < n:
        if lv[i]:
            j = i
            while j + 1 < n and lv[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def brackets(A, lv):
    out = []
    n = len(A)
    for i0, i1 in runs_of(lv):
        ra = A[i0 - 1] if i0 > 0 else A[i0] - 250.0
        fb = A[i1 + 1] if i1 + 1 < n else A[i1] + 250.0
        out.append(dict(i0=i0, i1=i1, ra=ra, rb=A[i0], fa=A[i1], fb=fb,
                        rmid=(ra + A[i0]) / 2, fmid=(A[i1] + fb) / 2))
    return out


def hough(recs, kgrid, t0grid):
    ra = np.array([r["ra"] for r in recs]); rb = np.array([r["rb"] for r in recs])
    rm = (ra + rb) / 2
    best = None
    for k in kgrid:
        Ra, Rb, Rm = k * ra, k * rb, k * rm
        m = Rm < NBITS * BIT + 400
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
    b = hough(recs, np.linspace(0.88, 1.14, 521), np.arange(-400.0, 600.0, 20.0))
    k, t0 = b[1], b[2]
    for w, nt in ((5e-4, 20.0), (1e-4, 4.0), (2e-5, 1.0)):
        b = hough(recs, k + np.linspace(-w, w, 41), t0 + np.linspace(-nt * 3, nt * 3, 31))
        k, t0 = b[1], b[2]
    return k, t0


def analyse(samples, bits):
    it = np.array([i for i, _, _ in samples], float)
    sl = np.array([s for _, s, _ in samples], int)
    lv = np.array([v for _, _, v in samples], bool)
    A = it * G + OFFS[sl]
    recs = brackets(A, lv)
    k, t0 = blind(recs)
    for r in recs:
        for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
            r[kk] = t0 + k * r[kk]
    recs = [r for r in recs if r["rmid"] < NBITS * BIT + 500]
    if len(recs) < 20:
        return None
    n = [int(round(recs[0]["rmid"] / BIT))]
    for j in range(1, len(recs)):
        n.append(n[-1] + int(round((recs[j]["rmid"] - recs[j - 1]["rmid"]) / BIT)))
    # ground truth pulse structure: recompute which bits each observed run covers
    # using true sample times is not available here, so use the *true* waveform:
    # a run covers bits n_true..n_true+s-1; derive from truth by simulating.
    st = Counter()
    # truth association through the true time base (synth is exact)
    return dict(recs=recs, n=n, lv=lv, A=A, k=k, t0=t0, st=st)


def truth_struct(payload, eps, phase):
    """Exact pulse structure from the synth model (no fitting)."""
    fr = frame(payload)
    bits = bits_of(fr)
    samples = synth_capture(payload, eps=eps, phase_ns=phase)
    it = np.array([i for i, _, _ in samples], float)
    sl = np.array([s for _, s, _ in samples], int)
    lv = np.array([v for _, _, v in samples], bool)
    total_cy = (640 - 1) * LOOP_CY + SLOT_POS_CY[-1]
    cy = it * LOOP_CY + np.array(SLOT_POS_CY)[sl]
    t_true = phase + cy * CY_NS / (1.0 + eps)
    out = []
    for i0, i1 in runs_of(lv):
        ks = sorted({int(t_true[m] // BIT) for m in range(i0, i1 + 1) if lv[m]})
        ks = [k for k in ks if 0 <= k < NBITS]
        if ks:
            out.append((ks[0], len(ks), bits[ks[-1]]))
    return bits, out, samples


def main():
    eps_pts = [-0.08, -0.075, -0.05, -0.025, 0.0, 0.025, 0.05, 0.075, 0.08]
    print("%7s %8s %8s %8s %8s %8s %7s" %
          ("eps", "adv_ok", "span_ok", "hid_ok", "last_ok", "amb%", "swal/f"))
    for eps in eps_pts:
        c = Counter()
        for name, payload in PATTERNS.items():
            for rep in range(3):
                phase = (rep * 83.0) % 250.0
                bits, tstruct, samples = truth_struct(payload, eps, phase)
                R = analyse(samples, bits)
                if R is None:
                    c["fail"] += 1
                    continue
                recs, n = R["recs"], R["n"]
                m = min(len(recs), len(tstruct))
                c["npulse"] += m
                # index advance
                for j in range(1, m):
                    adv_pred = n[j] - n[j - 1]
                    adv_true = tstruct[j][0] - tstruct[j - 1][0]
                    c["adv"] += 1
                    c["adv_ok"] += (adv_pred == adv_true)
                # span / last from fall bracket
                for j in range(m):
                    nn = n[j + 1] if j + 1 < len(recs) else NBITS
                    u = recs[j]["fa"] - n[j] * BIT
                    v = recs[j]["fb"] - n[j] * BIT
                    cands = []
                    for s in range(1, max(1, min(4, nn - n[j])) + 1):
                        for bb in (0, 1):
                            ht = (s - 1) * BIT + (H1 if bb else H0)
                            if ht > u - 120 and ht <= v + 120:
                                cands.append((s, bb, abs(ht - (u + v) / 2)))
                    if not cands:
                        cands = [(1, 0, 0.0)]
                    cands.sort(key=lambda x: x[2])
                    s, bb, _ = cands[0]
                    c["span"] += 1
                    c["span_ok"] += (s == tstruct[j][1])
                    c["last_ok"] += (bb == tstruct[j][2])
                    c["amb"] += (len(cands) > 1)
                # hidden zeros
                for j in range(m - 1):
                    hid_p = n[j + 1] - n[j] - tstruct[j][1]
                    hid_t = tstruct[j + 1][0] - tstruct[j][0] - tstruct[j][1]
                    c["hid"] += 1
                    c["hid_ok"] += (hid_p == hid_t)
                    c["swal"] += hid_t
        print("%+7.3f %8.4f %8.4f %8.4f %8.4f %7.2f %7.2f" %
              (eps, c["adv_ok"] / max(1, c["adv"]), c["span_ok"] / max(1, c["span"]),
               c["hid_ok"] / max(1, c["hid"]), c["last_ok"] / max(1, c["span"]),
               100 * c["amb"] / max(1, c["span"]), c["swal"] / 54))


main()
