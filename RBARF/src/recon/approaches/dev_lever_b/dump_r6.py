#!/usr/bin/env python3
"""Dump one R6/R8 frame bit-by-bit around every wrong bit: the owning
segment, both hypotheses' boundaries, the fall bracket, the samples that
landed in the bit's discriminating interval, and the truth."""
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import dwlib                                                   # noqa: E402
import v23lib as L                                             # noqa: E402
import crc                                                     # noqa: E402

e = dwlib.load_ref()
nd = int(sys.argv[1]) if len(sys.argv) > 1 else 48
e._configure(nd)
name = sys.argv[2] if len(sys.argv) > 2 else "full"
eps = float(sys.argv[3]) if len(sys.argv) > 3 else -0.010
t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 70.0

data = (L.prod_payloads() if nd == 48 else L.test_payloads())[name]
samples = L.linearize(L.capture(data, eps, t0))
tb = e._bits_of(e.HDR + crc.build_payload_v23(data) + e.TRL)
out, info = e.decode_ex(samples)
st = dwlib.analyze(e, samples, tb)
K, tau = st["K"], st["tau"]
print("payload=%s eps=%+.4f t0=%.1f -> cause=%s n_weak=%d n_tied=%d "
      "n_seg=%d K=%d tau=%d viol=%d" %
      (name, eps, t0, info["cause"], st["n_weak"], st["n_tied"],
       st["n_seg"], K, tau, len(st["wrong_mk"])))
sm = dwlib.sample_times(e, samples, K, tau)
cal = e._calibrate(samples, K, tau)
print("h0f=%s\nh1f=%s" % (cal.h0f, cal.h1f))
print("wrong payload' bits: %s" % st["wrong"])
for t in st["wrong"]:
    (k0, k1, fam, a_hat, u, v) = st["seg_of"][t]
    off = t - k0
    hb = off * e.BIT_U
    h0c, h1c = cal.h0f[fam], cal.h1f[fam]
    ins = [s for s in sm if s[0] == t]
    win = [s for s in ins if e.H0P < s[1] <= e.H0P + (e.H1P - e.H0P)]
    print("\nbit %d  truth=%d decoded=%d  margin=%d  dead_br=%s dead_cen=%s"
          % (t, tb[t], st["bits"][t], st["marg"][t],
             st["dead_br"][t], t in st["dead_cen"]))
    print("  seg k0=%d k1=%d L=%d fam=%d a_hat=%d  bracket u=%d v=%d "
          "(width %d TU)" % (k0, k1, k1 - k0, fam, a_hat, u, v, v - u))
    print("  bit off=%d  h0 boundary=%d  h1 boundary=%d   "
          "(need u < %d and %d <= v for dead)"
          % (off, hb + h0c, hb + h1c, hb + h0c, hb + h1c))
    print("  samples inside bit %d: %s" % (t, [(s[1], s[2]) for s in ins]))
    print("  samples in discriminating interval (%d,%d]: %s"
          % (e.H0P, e.H1P, [(s[1], s[2]) for s in ins
                            if e.H0P < s[1] <= e.H1P]))
    print("  truth bits %d..%d : %s" % (max(0, t - 6), min(e.NB, t + 7),
          "".join(str(tb[x]) for x in range(max(0, t - 6),
                                            min(e.NB, t + 7)))))
    print("  decoded    %d..%d : %s" % (max(0, t - 6), min(e.NB, t + 7),
          "".join(str(st["bits"][x]) for x in range(max(0, t - 6),
                                                    min(e.NB, t + 7)))))
    print("  margins    %d..%d : %s" % (max(0, t - 6), min(e.NB, t + 7),
          [st["marg"][x] for x in range(max(0, t - 6), min(e.NB, t + 7))]))
