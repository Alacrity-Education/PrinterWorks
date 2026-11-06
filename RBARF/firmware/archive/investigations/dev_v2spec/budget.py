from math import comb

# --- capture buffer sizing (v1 model, calibrated against report Sec.1) ---
# v1: 448 bits -> 224.0 loops nominal, "243 loops" at +8%.
def loops(nbits, eps):
    return nbits * 1250.0 / (2500.0 / (1.0 + eps))
print("v1 448b: nom %.1f  +7.5%% %.1f  +8%% %.1f  (report: 224.0 / 240.8 / 243)"
      % (loops(448, 0), loops(448, .075), loops(448, .08)))
slack = 243 - loops(448, .08)          # report's accounting margin (t0 + tail)
print("report accounting slack = %.2f loops" % slack)
for nb, name in ((216, "v2 test 27B"), (472, "v2 prod 59B"), (448, "v1 prod 56B")):
    print("%-14s nom %.1f  -7.5%% %.1f  +7.5%% %.1f  +8%% %.1f (=%.1f w/ slack)"
          % (name, loops(nb, 0), loops(nb, -.075), loops(nb, .075),
             loops(nb, .08), loops(nb, .08) + slack))
for buf in (256, 272, 288, 320):
    m = buf - (loops(472, .08) + slack)
    print("  prod buf %d B -> margin %.1f loops (%.0f us) at +8%%" % (buf, m, m * 2.3148))

# --- chase trial counts ---
for n in (4, 8, 12, 16):
    for w in (2, 3):
        print("n=%2d W<=%d  trials=%4d" % (n, w, sum(comb(n, k) for k in range(w + 1))))

# --- false-accept / abort bounds ---
for T in (16, 32, 64, 93, 256):
    print("T=%3d  CRC8-only FA<=%.4f   CRC8+CRC16 FA<=%.2e   P(false CRC8 stop)<=%.3f"
          % (T, T / 256.0, T / 2.0**24, 1 - (1 - 1/256.0) ** (T - 1)))

# --- N-repetition delivery vs per-copy emit probability ---
pts = [("bench -1.1%", 53/54.), ("-2.5%", 54/54.), ("-5%", 38/54.),
       ("-7.5%", 12/54.), ("+1%", 38/54.), ("+2.5%", 32/54.),
       ("+5%", 14/54.), ("+7.5%", 9/54.), ("+8%", 14/54.)]
print("%-12s %6s %7s %7s %7s %7s" % ("eps", "p", "N=3", "N=6", "N=9", "N=12"))
for name, p in pts:
    print("%-12s %6.3f %6.1f%% %6.1f%% %6.1f%% %6.1f%%"
          % (name, p, *[100 * (1 - (1 - p) ** n) for n in (3, 6, 9, 12)]))

# --- cycle budget ---
v1_total, v1_votes = 4.41e6, 0.252e6
grow = 472 / 448.
v2 = (v1_total - v1_votes) * grow + 27e3
print("v2 ticks = %.2f M (v1 %.2f M); +7%% silicon -> %.2f M = %.0f ms @16MHz"
      % (v2/1e6, v1_total/1e6, v2*1.07/1e6, v2*1.07/16e6*1e3))

# --- eps from K, and trim step ---
K_NOM = 52429
for eps in (-0.075, -0.0438, -0.0112, 0.0, 0.0373, 0.075):
    K = round(K_NOM / (1 + eps))
    back = (K_NOM - K) * 10000 // K
    print("eps %+7.3f%% -> K=%5d -> recovered %+6.2f%% (x100 int)" % (eps*100, K, back/100))
