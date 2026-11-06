"""Per-loop observed vs predicted dump for one capture (ground-truth fit)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa
from diag import fit_full  # noqa

meta, caps = load_dataset()
pat = sys.argv[1]
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
c = [x for x in caps if x["pattern"] == pat and x["rep"] == rep][0]
s = linearize(c["capture"])
frame = bytes.fromhex(c["frame"])
bits = bm._bits(frame)
L, B, sc, nx = fit_full(s, frame)
print(f"{pat} r{rep}  L={L:.2f} B={B:.1f} score={sc}/{nx}")
highs = [(i * bm.BIT, i * bm.BIT + (bm.T1H if v else bm.T0H))
         for i, v in enumerate(bits)]


def w(t):
    if t < 0 or t >= bm.FRAME_END:
        return 0
    i = int(t // bm.BIT)
    a, b = highs[i]
    return 1 if a <= t < b else 0


cur = {}
for it, sl, v in s:
    if it > 100:
        break
    cur.setdefault(it, {})[sl] = v
for it in sorted(cur):
    obs = "".join(str(cur[it].get(k, 9)) for k in range(8))
    pre = ""
    ph = ""
    for k in range(8):
        t = B + L * (it + bm.F[k])
        pre += str(w(t))
        ph += f"{int(t)//1250:4d}:{int(t)%1250:4d} "
    mark = "".join("." if a == b else "X" for a, b in zip(obs, pre))
    print(f"it{it:3d} obs {obs} pred {pre} {mark}  {ph}")
