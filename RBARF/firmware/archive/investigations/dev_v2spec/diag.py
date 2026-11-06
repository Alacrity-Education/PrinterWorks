"""Diagnostic: what separates a near-miss frame (chase should run) from a
broken frame (chase must not run)?"""
import sys, pathlib, pickle
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from patterns import PATTERNS                       # noqa: E402
from synth import synth_capture                     # noqa: E402
import ref_marg as ref, v21                         # noqa: E402

ref.VOTES = False
ND = 16; NPP = ND + 3
ref._configure(NPP)
EPS = [-0.04385, -0.03281, -0.02248, -0.01072, 0.00022, 0.01274, 0.02492,
       0.03733]
C = pathlib.Path(__file__).with_name("diag_cache.pkl")


def build():
    if C.exists():
        return pickle.load(C.open("rb"))
    rows = []
    for eps in EPS:
        for name, data in PATTERNS.items():
            pp = v21.payload_v21(data[:ND])
            tb = [(b >> (7 - i)) & 1 for b in pp for i in range(8)]
            for rep in range(3):
                s = synth_capture(pp, eps=eps, phase_ns=254.0 + (rep * 83.0) % 250.0)
                try:
                    st = ref.decode_state(s)
                except Exception:
                    st = None
                if st is None:
                    rows.append((eps, name, rep, None)); continue
                bits = st["bits"][32:32 + NPP * 8]
                mgv = st["mgv"][32:32 + NPP * 8]
                viol = sum(1 for t in range(ref.NB)
                           if ref.KNOWN[t] >= 0 and st["bits"][t] != ref.KNOWN[t])
                nw = sum(1 for i in range(NPP * 8) if bits[i] != tb[i])
                srt = sorted(range(NPP * 8), key=lambda k: (mgv[k], k))
                wrongranks = sorted([srt.index(i) for i in range(NPP * 8)
                                     if bits[i] != tb[i]])
                rows.append((eps, name, rep, dict(
                    nw=nw, viol=viol, inf=st["infeasible"], le=st["label_err"],
                    m=[mgv[k] for k in srt[:16]], wr=wrongranks[:6],
                    nlow=[sum(1 for k in range(NPP * 8) if mgv[k] <= th)
                          for th in (0, 2, 4, 8, 16, 32)])))
    pickle.dump(rows, C.open("wb"))
    return rows


rows = build()
print("%-9s %-4s %-4s %-4s %-5s  %-28s %-22s %s"
      % ("eps", "nw", "viol", "inf", "lerr", "margins rank0..7",
         "n(mgv<=0,2,4,8,16,32)", "wrong ranks"))
for eps, name, rep, d in rows:
    if d is None:
        print("%+.3f%% %-10s REFUSED-HARD" % (eps * 100, name)); continue
    if d["nw"] == 0 and eps in (-0.01072, 0.00022):
        continue
    print("%+7.3f%% %-10s nw=%-3d viol=%-2d inf=%-2d le=%-2d  %-30s %-24s %s"
          % (eps * 100, name, d["nw"], d["viol"], d["inf"], d["le"],
             str(d["m"][:8]), str(d["nlow"]), str(d["wr"])))
