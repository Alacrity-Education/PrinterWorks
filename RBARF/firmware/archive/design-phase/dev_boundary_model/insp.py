import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import linearize, load_dataset  # noqa

meta, caps = load_dataset()
pat = sys.argv[1] if len(sys.argv) > 1 else "ones"
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
c = [x for x in caps if x["pattern"] == pat and x["rep"] == rep][0]
s = linearize(c["capture"])
print("n samples", len(s), "payload", c["payload"], "frame", c["frame"])
fb = bytes.fromhex(c["frame"])
bits = "".join(f"{b:08b}" for b in fb)
print("frame bits:", bits)
lv = "".join(str(x[2]) for x in s)
# trim trailing zeros
last1 = lv.rfind("1")
print("last high sample idx", last1, "=> it", s[last1][0], "slot", s[last1][1])
print("levels:", lv[:last1 + 40])
# run lengths
runs = []
cur = lv[0]
n = 0
for ch in lv[:last1 + 1]:
    if ch == cur:
        n += 1
    else:
        runs.append((cur, n))
        cur = ch
        n = 1
runs.append((cur, n))
print("runs:", "".join(f"{c}{n} " for c, n in runs))
