#!/usr/bin/env python3
"""Parity + scoring harness for decoder.c (gcc build, ctypes).

Feeds the C decoder the RAW capture bytes (the exact production input)
and compares against (a) ground truth and (b) the Python embedded_ref
on all 54 real captures, plus synthetic production-size (48-byte
payload) frames.
"""
import ctypes
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import synth  # noqa: E402
from synth import _simulate  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "embedded_ref", ROOT / "approaches" / "embedded_ref.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)


def build(npay):
    so = HERE / f"decoder_{npay}.so"
    subprocess.run(
        ["gcc", "-O2", "-fPIC", "-shared", f"-DNB_PAYLOAD={npay}",
         "-o", str(so), str(HERE / "decoder.c")], check=True)
    lib = ctypes.CDLL(str(so))
    lib.ws_decode.restype = ctypes.c_uint8
    lib.ws_decode.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                              ctypes.c_char_p]
    return lib


def c_decode(lib, cap_bytes, npay):
    out = ctypes.create_string_buffer(npay)
    r = lib.ws_decode(cap_bytes, len(cap_bytes), out)
    return out.raw if r else None


def repack(samples, n_iter):
    """(i, s, v) triples -> raw capture bytes (cap_code.s layout)."""
    cap = bytearray(n_iter)
    for (i, s, v) in samples:
        if s < 6:
            if v:
                cap[i] |= 1 << (5 - s)
        else:                      # slots 6,7 of iter i live in byte i+1
            if i + 1 < n_iter and v:
                cap[i + 1] |= 1 << (7 - (s - 6))
    return bytes(cap)


meta, caps = load_dataset()

lib16 = build(16)
n_ok = n_match = 0
mism = []
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    cap_bytes = bytes.fromhex(c["capture"])
    exp = bytes.fromhex(c["payload"])
    d_c = c_decode(lib16, cap_bytes, 16)
    d_py = er.decode(linearize(c["capture"]), meta)
    n_ok += int(d_c == exp)
    if d_c == d_py:
        n_match += 1
    else:
        mism.append((name, d_c.hex() if d_c else None,
                     d_py.hex() if d_py else None))
print(f"C on real captures: {n_ok}/54 exact;  C==Python on {n_match}/54")
for m in mism[:8]:
    print("  MISMATCH", m)

# production-size frames (48-byte payloads) at bench + corners
er._configure(48)
lib48 = build(48)
PROD = {
    "zeros48": bytes(48),
    "ones48": bytes([0xFF] * 48),
    "aa48": bytes([0xAA] * 48),
    "p5548": bytes([0x55] * 48),
    "rnd48": bytes((i * 37 + 11) & 0xFF for i in range(48)),
    "grb48": bytes((i * 5) & 0xFF for i in range(48)),
}
n_ok = n_match = n_tot = 0
rows = []
for pname, payload in PROD.items():
    fr = synth.frame(payload)
    bits = [int(b) for byte in fr for b in f"{byte:08b}"]
    for eps, tag in ((synth.BENCH_EPS, "bench"), (-0.075, "slow"),
                     (0.075, "fast")):
        samples = _simulate(bits, eps, 0.0, 385.0, 640)
        cap640 = repack(samples, 640)
        # production buffer: first 256 bytes only (the real firmware
        # captures 256 loops, not 640)
        cap256 = cap640[:256]
        d_c = c_decode(lib48, cap256, 48)
        d_py = er.decode(samples, meta)
        n_tot += 1
        n_ok += int(d_c == payload)
        n_match += int(d_c == d_py)
        rows.append((f"{pname}/{tag}",
                     "OK" if d_c == payload else
                     ("None" if d_c is None else "WRONG"),
                     "py=" + ("OK" if d_py == payload else
                              ("None" if d_py is None else "WRONG"))))
print(f"\nC on production-size (256-B buffer): {n_ok}/{n_tot} exact; "
      f"C==Python(640) on {n_match}/{n_tot}")
for r in rows:
    print("  ", *r)
er._configure(16)
