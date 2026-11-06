"""Why does v2.3 deliver worse on SILICON?  Compare the lock/reconstruction
quality of the v2.2 and v2.3 real corpora, frame-for-frame."""
import importlib.util, json, sys, statistics as S
from pathlib import Path
NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
from harness import linearize

def fresh():
    sp = importlib.util.spec_from_file_location(
        "ev_d", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

for f, chk in (("captures_v22.json",4),("captures_v23.json",6),
               ("captures_v22_val.json",4),("captures_v23_val.json",6)):
    ev = fresh(); ev._configure(16, chk=chk)
    caps = json.loads((NEWIMPL/"data"/f).read_text())["captures"]
    errs=[]; Ks=[]; taus=[]; weaks=[]; viols=[]; nz=0
    for c in caps:
        truth=[int(b) for by in bytes.fromhex(c["frame"]) for b in f"{by:08b}"]
        st = ev.decode_state(linearize(c["capture"]))
        if st is None:
            errs.append(None); continue
        bits=st["bits"]
        e=sum(1 for i in range(min(len(bits),len(truth))) if bits[i]!=truth[i])
        errs.append(e); Ks.append(st["K"]); taus.append(st["tau"])
        weaks.append(st["n_weak"])
        viols.append(sum(1 for t in range(ev.NB)
                         if ev.KNOWN[t]>=0 and bits[t]!=ev.KNOWN[t]))
        if e==0: nz+=1
    ok=[e for e in errs if e is not None]
    print("=== %s (chk=%d, %d frames, NB=%d) ===" % (f, chk, len(caps), ev.NB))
    print("   recon BIT ERRORS in frame': mean %.2f  median %d  max %d   bit-exact %d/%d (%.1f%%)"
          % (S.mean(ok), S.median(ok), max(ok), nz, len(ok), 100.0*nz/len(ok)))
    print("   n_weak: mean %.2f max %d | marker violations: mean %.2f max %d"
          % (S.mean(weaks), max(weaks), S.mean(viols), max(viols)))
    print("   K: median %d  min %d  max %d | tau median %d"
          % (S.median(Ks), min(Ks), max(Ks), S.median(taus)))
    print("   error histogram:", {k: ok.count(k) for k in sorted(set(ok))[:12]})
    print()
