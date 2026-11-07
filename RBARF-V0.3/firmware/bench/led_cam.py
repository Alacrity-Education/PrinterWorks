#!/usr/bin/env python3
"""Webcam check of the LED output: record, isolate the LED, count glitches.

    led_cam.py NAME [--record SECONDS] [--device /dev/video0]

Records NAME.mkv from the webcam (fixed exposure, gain, white balance and
focus, 1080p MJPEG at 30 fps), finds the LED by temporal variance (the LED is
the only thing in the picture that changes colour), crops a 48 x 48 window
around it from every frame, and reports one-frame brightness spikes: frames
that are >= 12 % brighter than both neighbours. One 10 ms output frame at
double brightness integrated over a 33 ms exposure shows as ~ +30 %.

Writes NAME_series.npz (t, S = window light sum, C = per-channel sums,
centre) and NAME_summary.png (light + per-channel traces, spikes marked).
Without --record, re-analyses an existing NAME.mkv.

History: 2026-10-03, this found the dropped-first-bit bug in the PWM+DMA
output (LED0 decoding its value shifted left ~3 times/s; 69 and 48 spikes in
two 45 s baseline runs, 0 after the one-entry lead in ws2812_out/pwm.rs).
"""
import argparse
import subprocess

import cv2
import numpy as np

CAM_CTRLS = [
    "auto_exposure=1",  # manual
    "exposure_time_absolute=333",  # 33.3 ms = full coverage at 30 fps
    "gain=0",
    "exposure_dynamic_framerate=0",
    "white_balance_automatic=0",
    "focus_automatic_continuous=0",
    "focus_absolute=30",
]
WIN = 24  # half-size of the analysis window around the LED, px at 1080p


def record(name, device, seconds):
    subprocess.run(
        ["v4l2-ctl", "-d", device] + [f"--set-ctrl={c}" for c in CAM_CTRLS],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "v4l2", "-input_format", "mjpeg",
         "-video_size", "1920x1080", "-framerate", "30", "-i", device,
         "-t", str(seconds), "-c:v", "copy", f"{name}.mkv"],
        check=True,
    )


def locate(path):
    """Centre (x, y) at full resolution of the highest-variance blob."""
    cap = cv2.VideoCapture(path)
    acc = acc2 = None
    n = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        s = cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32)
        if acc is None:
            acc = np.zeros_like(s)
            acc2 = np.zeros_like(s)
        acc += s
        acc2 += s * s
        n += 1
    std = np.sqrt(np.maximum(acc2 / n - (acc / n) ** 2, 0)).max(axis=2)
    mask = (std >= np.percentile(std, 99.9)).astype(np.uint8)
    num, lab, _, cent = cv2.connectedComponentsWithStats(mask, 8)
    best = max(range(1, num), key=lambda i: std[lab == i].max())
    return int(cent[best][0] * 4), int(cent[best][1] * 4), n


def series(path, cx, cy):
    cap = cv2.VideoCapture(path)
    t, S, C = [], [], []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        w = f[cy - WIN:cy + WIN, cx - WIN:cx + WIN].astype(np.float32)
        t.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
        S.append(w.sum())
        C.append(w.sum(axis=(0, 1)))
    return np.array(t), np.array(S), np.array(C)


def spikes(sig, k=3, thr=0.12):
    out = []
    for i in range(k, len(sig) - k):
        base = np.median(np.concatenate([sig[i - k:i], sig[i + 1:i + 1 + k]]))
        if sig[i] > base * (1 + thr) and sig[i - 1] <= base * (1 + thr / 2) \
                and sig[i + 1] <= base * (1 + thr / 2):
            out.append(i)
    return np.array(out, dtype=int)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--record", type=float, metavar="SECONDS")
    ap.add_argument("--device", default="/dev/video0")
    a = ap.parse_args()
    if a.record:
        record(a.name, a.device, a.record)
    path = f"{a.name}.mkv"
    cx, cy, n = locate(path)
    t, S, C = series(path, cx, cy)
    sp = spikes(S)
    dur = t[-1] - t[0]
    np.savez(f"{a.name}_series.npz", t=t, S=S, C=C, centre=(cx, cy))
    print(f"{a.name}: {n} frames, {dur:.1f} s, LED at ({cx},{cy}), "
          f"one-frame spikes: {len(sp)} = {len(sp) / dur:.2f}/s")
    bins = np.arange(0, dur + 5, 5)
    h = np.histogram(t[sp], bins)[0] if len(sp) else np.zeros(len(bins) - 1, int)
    print("  per 5 s bin:", " ".join(str(int(x)) for x in h))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(18, 7), sharex=True)
    ax[0].plot(t, S / 1e3, lw=0.7)
    ax[0].plot(t[sp], S[sp] / 1e3, "rv", ms=5)
    ax[0].set_ylabel("LED light (k)")
    for ch, col in ((2, "r"), (1, "g"), (0, "b")):
        ax[1].plot(t, C[:, ch] / 1e3, col, lw=0.7)
    ax[1].set_ylabel("per channel (k)")
    ax[1].set_xlabel("video time s")
    for x in ax:
        x.grid(alpha=.3)
    plt.suptitle(f"{a.name}: {len(sp)} one-frame spikes in {dur:.0f} s")
    plt.tight_layout()
    plt.savefig(f"{a.name}_summary.png", dpi=80)


if __name__ == "__main__":
    main()
