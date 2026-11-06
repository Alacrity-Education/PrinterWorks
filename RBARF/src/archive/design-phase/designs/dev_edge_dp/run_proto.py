import sys, time
import numpy as np
import model as M
import proto

meta, D = M.load()
o = np.array(M.O_NOM)
# Delta = nominal receiver ns per WS2812 bit = 1250 * k ; k ~ 0.997..1.006
deltas = np.arange(1245.0, 1259.01, 1.0)
phis = np.arange(-400.0, 401.0, 50.0)

kw = {}
for a in sys.argv[1:]:
    k, v = a.split("=")
    kw[k] = float(v)

t0 = time.time()
nex = 0
nbit_err = 0
rows = []
for d in D:
    tau = proto.build_tau(d["idx"], o)
    obs = np.array(d["obs"], dtype=float)
    c, bits, Dl, ph = proto.decode(tau, obs, phis, deltas, **kw)
    pay = proto.bits_to_payload(bits)
    exact = pay == d["payload"]
    nex += exact
    be = int((bits[32:160] != np.array(M.frame_bits(d["payload"]))[32:160]).sum())
    nbit_err += be
    nby = sum(1 for a_, b_ in zip(pay, d["payload"]) if a_ == b_)
    rows.append((d["pattern"], d["rep"], exact, be, nby, Dl, ph))
for r in rows:
    print(f"{r[0]:12s}r{r[1]} exact={int(r[2])} biterr={r[3]:3d} bytes={r[4]:2d}/16 "
          f"D={r[5]:.1f} phi={r[6]:6.0f}")
print(f"EXACT {nex}/{len(D)}  total payload bit errors {nbit_err}/{len(D)*128} "
      f"({time.time()-t0:.0f}s)  kw={kw}")
