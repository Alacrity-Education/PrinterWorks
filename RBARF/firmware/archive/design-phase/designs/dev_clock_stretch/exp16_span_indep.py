"""Assumption-light check of L: the frame's last falling edge is at
191*1250+700 = 239450 ns (exact, crystal).  The capture is edge-triggered
so the first rising edge is at t=0, just before sample (0,0).
The last high sample of the capture therefore brackets 239450 ns.

L is obtained from  239450 = phi + (i_last + a[s_last]) * L,  with phi the
(small, bounded) trigger offset.  Solve for L over the plausible phi
range and compare against 2507.3 (harness) and ~2499.8 (joint fit).
Only the slot FRACTION a[s] is assumed; its uncertainty is bounded by
+-1 slot = at most 0.2 loop, and we report that band too.
"""
import numpy as np
from common import load_all

A40 = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
A37 = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 37.0
T_LAST_FALL = 191 * 1250.0 + 700.0

meta, caps = load_all()
print(f"{'pattern':11s} {'rep':>3s} {'it_last':>7s} {'sl':>2s} "
      f"{'u(A40)':>7s} {'L|phi=0':>8s} {'L|phi=250':>9s} {'u@2507.3':>8s} {'u@2499.8':>8s}")
rows = []
for cap in caps:
    hi = np.nonzero(cap["lev"] == 1)[0]
    n = hi[-1]
    it, sl = cap["it"][n], cap["slot"][n]
    # bracket: last high sample <= edge < next sample
    u_lo = it + A40[sl]
    nn = n + 1
    u_hi = cap["it"][nn] + A40[cap["slot"][nn]] if nn < len(cap["it"]) else u_lo + .2
    um = .5 * (u_lo + u_hi)
    L0 = T_LAST_FALL / um
    L250 = (T_LAST_FALL - 250.0) / um
    rows.append((L0, L250, um))
    print(f"{cap['pattern']:11s} {cap['rep']:3d} {it:7d} {sl:2d} "
          f"{um:7.3f} {L0:8.2f} {L250:9.2f} "
          f"{T_LAST_FALL/2507.3:8.3f} {T_LAST_FALL/2499.8:8.3f}")
r = np.array(rows)
print(f"\nL from span, phi=0   : mean={r[:,0].mean():.2f} std={r[:,0].std():.2f}")
print(f"L from span, phi=250 : mean={r[:,1].mean():.2f} std={r[:,1].std():.2f}")
print(f"u_last: mean={r[:,2].mean():.3f}  "
      f"predicted by L=2507.3 -> {T_LAST_FALL/2507.3:.3f}, "
      f"by L=2499.8 -> {(T_LAST_FALL-150)/2499.8:.3f} (phi=150)")

# Loop-count of the frame: count loops between first and last rising edge
print("\n== first/last rising edge iteration ==")
for cap in caps[:6]:
    d = np.diff(cap["lev"].astype(int)); ri = np.nonzero(d > 0)[0]
    print(f"{cap['pattern']:11s} {cap['rep']} first rise it={cap['it'][ri[0]]} "
          f"slot={cap['slot'][ri[0]]}  last rise it={cap['it'][ri[-1]]} "
          f"slot={cap['slot'][ri[-1]]}  nrise={len(ri)}")
