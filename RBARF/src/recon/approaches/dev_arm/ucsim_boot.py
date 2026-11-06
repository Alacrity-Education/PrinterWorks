#!/usr/bin/env python3
"""ucsim boot smoke test for the arm-diagnostic image (bench-only).

Proves reset vector -> GSINIT -> CKDIVR/TIM4/TIM2 config -> ws2812_out_init
executes, and reports whether ucsim's TIM4 tick and the new TIM2 us
timebase actually run (the diagnostic's stamps depend on TIM2).
Every child runs under `setsid timeout -k` + a pkill sweep.
"""
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

SC = Path(__file__).resolve().parent
IHX = str(SC / "rbarf_arm.ihx")
PORT = 21593
BRK_RIM = 0x828B          # the `rim` right after ws2812_out_init
MS = 0x377                # _ms_counter (tick.c)
TIM2_CNTRH = 0x530C


def sweep():
    subprocess.run(["pkill", "-x", "ucsim_stm8"], capture_output=True)
    time.sleep(0.15)
    if subprocess.run(["pgrep", "-x", "ucsim_stm8"],
                      capture_output=True).returncode == 0:
        subprocess.run(["pkill", "-9", "-x", "ucsim_stm8"],
                       capture_output=True)
        time.sleep(0.15)


class U:
    def __init__(self):
        self.p = subprocess.Popen(
            ["setsid", "timeout", "-k", "5", "90", "ucsim_stm8",
             "-t", "STM8S208", "-q", "-Z", str(PORT), IHX],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True)
        time.sleep(0.6)
        self.s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
        self.cmd("")

    def cmd(self, c, wait=0.3):
        self.s.sendall((c + "\n").encode())
        time.sleep(wait)
        self.s.setblocking(False)
        buf = b""
        try:
            while True:
                ch = self.s.recv(65536)
                if not ch:
                    break
                buf += ch
        except BlockingIOError:
            pass
        self.s.setblocking(True)
        return buf.decode(errors="replace")

    def until(self, c, needle, timeout=40.0):
        self.s.sendall((c + "\n").encode())
        buf = ""
        end = time.time() + timeout
        while time.time() < end:
            time.sleep(0.2)
            self.s.setblocking(False)
            try:
                while True:
                    ch = self.s.recv(65536)
                    if not ch:
                        break
                    buf += ch.decode(errors="replace")
            except BlockingIOError:
                pass
            self.s.setblocking(True)
            if needle in buf:
                break
        return buf

    def read(self, addr, n):
        out = self.cmd("dump 0x%x 0x%x" % (addr, addr + n - 1), 0.25)
        vals = []
        for line in out.splitlines():
            m = re.match(r"0x[0-9a-f]+\s+((?:[0-9a-f]{2}\s+)+)", line)
            if m:
                vals += [int(x, 16) for x in m.group(1).split()]
        return vals[:n]

    def close(self):
        try:
            self.cmd("kill", 0.1)
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()
        sweep()


def main():
    sweep()
    u = U()
    rc = 0
    try:
        u.cmd("break 0x%x" % BRK_RIM, 0.2)
        out = u.until("run", "Stop at", timeout=40)
        st = u.cmd("state", 0.3)
        pc = re.search(r"PC= 0x([0-9a-fA-F]+)", st)
        pcv = int(pc.group(1), 16) if pc else -1
        ok = BRK_RIM <= pcv <= BRK_RIM + 1
        print("boot to 0x%04X (rim after TIM2 init + ws2812_out_init): %s "
              "(PC=0x%04X)" % (BRK_RIM, "REACHED" if ok else "NOT REACHED",
                               pcv))
        if not ok:
            print(out[-400:])
            rc = 1
        u.cmd("break clear", 0.2)
        ms0 = u.read(MS, 2)
        t20 = u.read(TIM2_CNTRH, 2)
        u.cmd("step 200000", 3.0)
        ms1 = u.read(MS, 2)
        t21 = u.read(TIM2_CNTRH, 2)
        print("TIM4 ms_counter: %s -> %s   (%s)"
              % (ms0, ms1, "TICKING" if ms1 != ms0 else "not simulated"))
        print("TIM2 CNTRH/L   : %s -> %s   (%s)"
              % (t20, t21, "COUNTING" if t21 != t20 else "not simulated"))
    finally:
        u.close()
    if subprocess.run(["pgrep", "-x", "ucsim_stm8"],
                      capture_output=True).returncode == 0:
        print("STRAY ucsim_stm8 STILL RUNNING")
        rc = 1
    else:
        print("stray check: clean")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
