import re, sys, time, subprocess
sys.path.insert(0, "..")
sys.path.insert(0, "../..")
from pathlib import Path
HERE = Path(".").resolve()
sys.path.insert(0, str(HERE.parents[1]))
from harness import load_dataset, linearize
import importlib.util
spec = importlib.util.spec_from_file_location("embedded_v2", HERE.parents[1] / "approaches" / "embedded_v2.py")
v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
import ucsim_bitexact as U

corpus, pat, rep, check = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
U.ASMDEC = True
v2._configure(16, check=bool(check))
_, caps = load_dataset(str(HERE.parents[2] / "data" / corpus))
cap = next(c for c in caps if c.get("pattern")==pat and int(c.get("rep",0))==rep)
raw = bytes.fromhex(cap["capture"])[:256]
U.gen_cap(raw)
sym = U.build(bool(check), True)
sim = U.Ucsim(str(HERE / "sim_v2.ihx"), 21600)
try:
    sim.run_decode()
    zp = sim.read(0xBA, 0x28)
finally:
    sim.close()
def w(off, signed=True):
    v = (zp[off]<<8)|zp[off+1]
    if signed and v >= 0x8000: v -= 0x10000
    return v
asmv = dict(
  c_lo=[w(0),w(2)], c_hi=[w(4),w(6)], c_n=[zp[8],zp[9]],
  h0c=w(0xA), h1c=w(0xC), d56=[(zp[0xE]^0x80)-0x80, (zp[0xF]^0x80)-0x80],
  labx0=[w(0x10),w(0x12)], labx1=[w(0x14),w(0x16)],
  labx0b=[w(0x18),w(0x1A)], labx1b=[w(0x1C),w(0x1E)],
  c0=[w(0x20),w(0x22)], gap=[w(0x24),w(0x26)])

# reference with cal capture
samples = linearize(raw.hex())
st = {}
orig_cal = v2._calibrate
hold = {}
def spy(samples, K, tau):
    cal = orig_cal(samples, K, tau)
    hold['cal'] = cal
    return cal
v2._calibrate = spy
d, info = v2.decode_ex(samples)
cal = hold['cal']
refv = dict(
  c_lo=[cal.lo0,cal.lo1], c_hi=[cal.hi0,cal.hi1], c_n=[min(cal.n0,255),min(cal.n1,255)],
  h0c=cal.h0c, h1c=cal.h1c,
  d56=[cal.h0f[5]-cal.h0c, cal.h0f[6]-cal.h0c],
  labx0=[cal.labx0[5],cal.labx0[6]], labx1=[cal.labx1[5],cal.labx1[6]],
  labx0b=[cal.labx0b[5],cal.labx0b[6]], labx1b=[cal.labx1b[5],cal.labx1b[6]],
  c0=[cal.c0[5],cal.c0[6]], gap=list(cal.gap56))
print("field           asm                      ref")
for k in asmv:
    mark = "" if asmv[k]==refv[k] else "   <<< DIFF"
    print("%-8s %-24s %-24s%s" % (k, asmv[k], refv[k], mark))
print("py info:", {k:info.get(k) for k in ("path","cause","n_weak","n_tied","label_err","infeasible")})
