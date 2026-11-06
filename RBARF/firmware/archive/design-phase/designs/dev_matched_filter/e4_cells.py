"""E4: per-bit-cell sample census using an oracle time base.

For every capture and every one of the 192 frame bits, report how many
samples land in the cell, how many read HIGH, and whether the bit is
"evidence-free" (a 0-bit whose T0H produced no high sample, or a 1-bit
whose high produced none).  Focus on the header 00 byte (bits 8..15).
"""
import json
import sys
from collections import Counter

import numpy as np

from common import load, BIT_NS
from mf import phase

cal = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "e2_oracle.json"))
G = cal.get("G", 40.0)
P = np.array(cal.get("P", [0., 4., 8., 12., 16., 20., 26., 31.]))
H1 = cal.get("h1", cal.get("H1", 750.0))
H0 = cal.get("h0", cal.get("H0", 375.0))
RES = cal["res"]
NW = 900

meta, caps = load()
print(f"grid G={G} P={list(P)} h1={H1} h0={H0}")

hdr_zero_hi = Counter()          # highs per header-00 bit
zero_hi = Counter()              # highs per payload 0-bit
one_hi = Counter()
cell_n = Counter()
lost_by_bitpos = Counter()
tot0 = tot1 = 0
lost0 = lost1 = 0
hdr_lost_per_cap = []
merged = 0
tot_1pairs = 0

for c in caps:
    t0, k = RES[c["key"]][:2]
    u = phase(c["it"][:NW], c["sl"][:NW], G, P)
    t = t0 + k * u
    lv = c["lv"][:NW]
    b = np.floor(t / BIT_NS).astype(int)
    bits = c["bits"]
    hl = 0
    for j in range(192):
        sel = (b == j)
        n = int(sel.sum())
        nh = int(lv[sel].sum())
        cell_n[n] += 1
        if bits[j]:
            one_hi[nh] += 1
            tot1 += 1
            if nh == 0:
                lost1 += 1
                lost_by_bitpos[j] += 1
        else:
            tot0 += 1
            zero_hi[nh] += 1
            if 8 <= j < 16:
                hdr_zero_hi[nh] += 1
                if nh == 0:
                    hl += 1
            if nh == 0:
                lost0 += 1
                lost_by_bitpos[j] += 1
    hdr_lost_per_cap.append(hl)
    # merged 1-pairs: consecutive 1 bits with no low sample between the
    # two cells' high groups
    for j in range(191):
        if bits[j] and bits[j + 1]:
            tot_1pairs += 1
            s = (b == j) | (b == j + 1)
            idx = np.where(s)[0]
            seq = lv[idx]
            # low samples strictly between first high of cell j and last
            # high of cell j+1
            hi = np.where(seq == 1)[0]
            if len(hi) >= 2 and not (seq[hi[0]:hi[-1]] == 0).any():
                merged += 1

print("samples per bit cell:", dict(sorted(cell_n.items())))
print(f"0-bits total {tot0}, no-high (swallowed) {lost0} = {100*lost0/tot0:.2f}%")
print(f"1-bits total {tot1}, no-high {lost1} = {100*lost1/tot1:.3f}%")
print("highs-per-0-bit hist:", dict(sorted(zero_hi.items())))
print("highs-per-1-bit hist:", dict(sorted(one_hi.items())))
print("header-00 byte (bits 8..15) highs-per-bit hist:", dict(sorted(hdr_zero_hi.items())))
print("header-00 swallowed per capture:", Counter(hdr_lost_per_cap))
print(f"merged 1-pairs {merged}/{tot_1pairs} = {100*merged/max(tot_1pairs,1):.2f}%")
top = sorted(lost_by_bitpos.items(), key=lambda x: -x[1])[:20]
print("worst bit positions (frame index -> #captures swallowed):", top)
