import importlib.util, json, sys, statistics as St
from collections import Counter
from pathlib import Path
NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
from harness import linearize

rows = json.loads(Path(sys.argv[1]).read_text())

def fresh(hdr, trl):
    sp = importlib.util.spec_from_file_location(
        "ev_v", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    m.HDR_V23 = bytes.fromhex(hdr); m.TRL_V23 = bytes.fromhex(trl)
    m._configure(16, chk=6)          # re-derives KNOWN from the new markers
    assert m.HDR == bytes.fromhex(hdr) and m.N_MK == 48
    return m

variants = {}
for r in rows:
    variants.setdefault(r["variant"], (r["hdr"], r["trl"]))

print("variant      hdr    trl     n   delivered      refused  WRONG | "
      "recon bit-exact  mean err  n_weak  refusal causes")
summ = {}
for v in sorted(variants):
    hdr, trl = variants[v]
    ev = fresh(hdr, trl)
    caps = [r for r in rows if r["variant"] == v]
    d = w = ref = 0; causes = Counter(); errs = []; weaks = []; nz = 0
    for c in caps:
        truth16 = bytes.fromhex(c["payload"])[:16]
        samples = linearize(c["capture"])
        st = ev.decode_state(samples)
        if st is not None:
            tb = [int(b) for by in bytes.fromhex(c["frame"]) for b in f"{by:08b}"]
            e = sum(1 for i in range(min(len(st["bits"]), len(tb)))
                    if st["bits"][i] != tb[i])
            errs.append(e); weaks.append(st["n_weak"]); nz += (e == 0)
        out, info = ev.decode_ex(samples)
        if out is None: ref += 1; causes[info["cause"]] += 1
        elif out == truth16: d += 1
        else: w += 1
    n = len(caps)
    summ[v] = (d, n, w, nz, len(errs))
    print("%-11s %-6s %-6s %3d  %3d (%5.1f%%)  %3d (%5.1f%%)  %d   | "
          "%3d/%3d (%5.1f%%)  %.2f      %.2f    %s"
          % (v, hdr, trl, n, d, 100.0*d/n, ref, 100.0*ref/n, w,
             nz, len(errs), 100.0*nz/len(errs), St.mean(errs),
             St.mean(weaks), dict(causes)))

print()
base = summ["V0_spec"]
for v in ("V1_hdr00", "V2_trl00", "V3_both00"):
    d, n, w, nz, ne = summ[v]
    print("%-10s vs V0_spec: delivery %+.1f pp   recon bit-exact %+.1f pp"
          % (v, 100.0*d/n - 100.0*base[0]/base[1],
             100.0*nz/ne - 100.0*base[3]/base[4]))

# paired McNemar on delivery, same pattern/rep cell
print()
for v in ("V1_hdr00", "V2_trl00", "V3_both00"):
    ev0 = fresh(*variants["V0_spec"]); evv = fresh(*variants[v])
    b = c = 0
    for r0 in [r for r in rows if r["variant"] == "V0_spec"]:
        rv = next(r for r in rows if r["variant"] == v
                  and r["pattern"] == r0["pattern"] and r["rep"] == r0["rep"])
        t = bytes.fromhex(r0["payload"])[:16]
        o0 = ev0.decode_ex(linearize(r0["capture"]))[0] == t
        ov = evv.decode_ex(linearize(rv["capture"]))[0] == t
        if ov and not o0: b += 1
        elif o0 and not ov: c += 1
    chi = (abs(b-c)-1)**2/(b+c) if b+c else 0.0
    print("  %-10s wins %2d, loses %2d  chi2=%.2f  %s"
          % (v, b, c, chi, "SIGNIFICANT" if chi > 3.84 else "n.s."))
