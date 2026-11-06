"""Non-circular slot-7 position test: fit phi from slots 0..6 only."""
import json
import numpy as np
from bm_common import BIT_NS, load
from bm_phase import C, viterbi, PHI, STEP, NL, H1, H0

D = np.arange(-120.0, 121.0, 5.0)

def cost_grid_sub(c, tau, slots):
    bits = c["bits"]; hwv = np.where(bits == 1, H1, H0); nb = len(bits)
    lv = np.zeros((NL, 8), np.int8)
    for k in range(len(c["lv"])):
        i, s = c["it"][k], c["sl"][k]
        if i < NL: lv[i, s] = c["lv"][k]
    I = np.arange(NL, dtype=float)[:, None]
    acc = np.zeros((NL, len(PHI)), np.int16)
    for s in slots:
        t = 2500.0 * I + tau * C[s] + PHI[None, :]
        j = np.floor(t / BIT_NS).astype(np.int64)
        ok = (j >= 0) & (j < nb); jc = np.clip(j, 0, nb - 1)
        pred = (ok & ((t - jc * BIT_NS) < hwv[jc])).astype(np.int8)
        acc += (pred != lv[:, s][:, None]).astype(np.int16)
    return acc, lv

def main():
    meta, caps = load(); fin = json.load(open("bm_final.json"))
    for probe in (7, 6, 2):
        rest = [s for s in range(8) if s != probe]
        tot = np.zeros(len(D)); n = 0
        for c in caps:
            tau = fin[c["key"]]["tau"]
            cg, lv = cost_grid_sub(c, tau, rest)
            phi, _ = viterbi(cg[:94])
            hwv = np.where(c["bits"] == 1, H1, H0)
            i = np.arange(94)
            base = 2500.0 * i + phi + tau * C[probe]
            t = base[:, None] + D[None, :]
            j = np.floor(t / BIT_NS).astype(np.int64)
            ok = (j >= 0) & (j < 192); jc = np.clip(j, 0, 191)
            pred = (ok & ((t - jc * BIT_NS) < hwv[jc])).astype(np.int8)
            tot += (pred != lv[:94, probe][:, None]).sum(axis=0); n += 94
        b = int(np.argmin(tot)); z = int(np.argmin(np.abs(D)))
        print(f"slot {probe}: n={n} best_delta={D[b]:+.0f} ns "
              f"mism@0={int(tot[z])} mism@best={int(tot[b])}")
        print("   ", " ".join(f"{int(D[k]):+4d}:{int(tot[k]):4d}"
                              for k in range(0, len(D), 2)))

main()
