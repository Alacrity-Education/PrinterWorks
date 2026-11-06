"""Production-scale (48 data bytes -> 51 B payload' -> 59 B frame, 472 bits)
end-to-end v2.1 single-shot evaluation with the final chase policy."""
import sys, pathlib, pickle, random
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from patterns import PATTERNS, VAL_PATTERNS           # noqa: E402
from synth import synth_capture                       # noqa: E402
import ref_marg as ref, v21                           # noqa: E402

ref.VOTES = False
ND = 48; NPP = ND + 3
ref._configure(NPP)
EPSL = [-0.08, -0.075, -0.05, -0.04385, -0.03281, -0.025, -0.02248,
        -0.01072, -0.01, 0.0, 0.00022, 0.01, 0.01274, 0.025, 0.02492,
        0.03733, 0.05, 0.075, 0.08]
C = pathlib.Path(__file__).with_name("prod_cache.pkl")

rng = random.Random(20260906)
DATA = {}
for n, p in PATTERNS.items():
    DATA["t_" + n] = p * 3
for n, p in list(VAL_PATTERNS.items())[:6]:
    DATA["v_" + n] = p * 3
DATA["grb_ramp"] = bytes((i * 5) & 0xFF for i in range(48))
for i in range(5):
    DATA["rnd%d" % i] = bytes(rng.randrange(256) for _ in range(48))


def gather():
    out = pickle.load(C.open("rb")) if C.exists() else {}
    todo = [(e, n, r) for e in EPSL for n in DATA for r in range(3)
            if (round(e, 6), n, r) not in out]
    for i, (eps, name, rep) in enumerate(todo):
        pp = v21.payload_v21(DATA[name])
        s = synth_capture(pp, eps=eps, phase_ns=254.0 + (rep * 83.0) % 250.0)
        try:
            st = ref.decode_state(s)
        except Exception:
            st = None
        if st is None:
            rec = None
        else:
            bits, mgv = st["bits"], st["mgv"]
            viol = sum(1 for t in range(ref.NB)
                       if ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t])
            gate = (viol > 0 or st["infeasible"] > ref.GATE_INFEAS
                    or st["label_err"] > ref.GATE_LABERR)
            rec = (bits[32:32 + NPP * 8], mgv[32:32 + NPP * 8], gate)
        out[(round(eps, 6), name, rep)] = (rec, bytes(DATA[name]))
        if i % 100 == 0:
            print("  ... %d/%d" % (i, len(todo)), flush=True)
    pickle.dump(out, C.open("wb"))
    return out


recs = gather()


def run(keys, td=8, tie=3, N=8, W=2, T=37, ordering="dfirst", fb=False):
    c = Counter(); tr = []
    for k in keys:
        rec, truth = recs[k]
        if rec is None or rec[2]:
            c["refuse"] += 1; continue
        bits, mgv, _ = rec
        n0 = sum(1 for v in mgv if v == 0)
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
        if path == "direct":
            if n0 > td:
                c["refuse"] += 1; continue
            c["ok_direct" if got == truth else "CAT"] += 1; continue
        if n0 > tie:
            c["refuse"] += 1; continue
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=N, WMAX=W, TMAX=T,
                                  ordering=ordering, fallback=fb)
        tr.append(nt)
        if got is None:
            c["refuse"] += 1
        else:
            c["ok_chase" if got == truth else "CAT"] += 1
    return c, tr


def line(tag, c, tr, n):
    ok = c["ok_direct"] + c["ok_chase"]
    print("%-40s n=%4d deliver %4d (%5.1f%%) dir %4d chase %3d refuse %4d "
          "CAT %d  trials mean %5.1f max %3d"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["refuse"], c["CAT"], sum(tr) / max(1, len(tr)),
             max(tr) if tr else 0))


allk = list(recs)
print("=== PRODUCTION 48 B data / 472-bit frame, %d decodes ===" % len(allk))
for td, tie, N, W, T, fb in ((255, 3, 8, 2, 37, False), (8, 3, 8, 2, 37, False),
                             (8, 3, 8, 2, 37, True), (8, 3, 8, 3, 93, False),
                             (8, 4, 8, 2, 37, False), (8, 2, 8, 2, 37, False),
                             (8, 3, 4, 2, 11, False), (8, 3, 0, 0, 1, False)):
    c, tr = run(allk, td, tie, N, W, T, fb=fb)
    line("tdir<=%-3d tie<=%d N=%d W<=%d T=%2d fb=%d" % (td, tie, N, W, T, fb),
         c, tr, len(allk))
print("\n=== per eps, FINAL (tdir<=8 tie<=3 N=8 W<=2 T=37 dfirst fb=off) ===")
for e in EPSL:
    ks = [k for k in recs if k[0] == round(e, 6)]
    c, tr = run(ks)
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))
print("\n=== per eps, chase DISABLED (direct only) ===")
for e in EPSL:
    ks = [k for k in recs if k[0] == round(e, 6)]
    c, tr = run(ks, N=0, W=0, T=1)
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))
