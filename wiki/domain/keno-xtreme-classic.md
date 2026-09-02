---
type: domain
tags: [keno, paytable, classic, keno-xtreme]
updated: 2026-09-02
---

# Keno Xtreme Classic — picks and multipliers

Stake Keno Xtreme **Classic** HUD (docx: Normal). Source:
[[sources/keno-xtreme-classic-hud]] (screenshots 2026-09-01). Board: pool 40,
draw 10, picks 1–10. Bottom-row `Nx` is **hits**.

luma-keno Off `classic` is the analogue — see [[codebase/luma-keno]]. How
the shipped multipliers are generated (RTP identity, geometric ladder,
lattice): [[concepts/keno-paytable-generation]]. The
competitor HUD below is 42–91% RTP; the shipped chart is a geometric
leftover-fill onto 0.9650 with the same zeros. Maxes follow the HUD on picks
2, 7–10; **picks 3–6 were cut 2026-09-01** (perfect-hit tops read too big):
40/100/300/500 → 17.5/30/75/200 (lattice-legal snaps).

## All picks

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.50 | 2.50 | | | | | | | | | | **2.50** |
| **2** | 0.00 | 1.50 | 5.00 | | | | | | | | | **5.00** |
| **3** | 0.00 | 0.00 | 2.50 | 40.00 | | | | | | | | **40.00** |
| **4** | 0.00 | 0.00 | 1.50 | 9.00 | 100.0 | | | | | | | **100.0** |
| **5** | 0.00 | 0.00 | 1.10 | 4.00 | 10.00 | 300.0 | | | | | | **300.0** |
| **6** | 0.00 | 0.00 | 0.00 | 2.00 | 9.00 | 100.0 | 500.0 | | | | | **500.0** |
| **7** | 0.00 | 0.00 | 0.00 | 1.10 | 3.00 | 9.00 | 100.0 | 600.0 | | | | **600.0** |
| **8** | 0.00 | 0.00 | 0.00 | 1.50 | 3.00 | 9.00 | 40.00 | 200.0 | 750.0 | | | **750.0** |
| **9** | 0.00 | 0.00 | 0.00 | 1.10 | 1.50 | 3.00 | 5.00 | 50.00 | 400.0 | 900.0 | | **900.0** |
| **10** | 0.00 | 0.00 | 0.00 | 1.10 | 1.50 | 2.00 | 4.00 | 10.00 | 50.00 | 500.0 | 1000 | **1000** |

Shipped luma-keno Off `classic` (geometric, 2026-09-01) — pick_10 max 1000×:

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.40 | 2.60 | | | | | | | | | | **2.60** |
| **2** | 0.00 | 1.70 | 5.40 | | | | | | | | | **5.40** |
| **3** | 0.00 | 0.00 | 5.50 | 17.50 | | | | | | | | **17.5** |
| **4** | 0.00 | 0.00 | 2.60 | 8.60 | 30.0 | | | | | | | **30** |
| **5** | 0.00 | 0.00 | 1.30 | 4.90 | 19.50 | 75.0 | | | | | | **75** |
| **6** | 0.00 | 0.00 | 0.00 | 3.90 | 14.80 | 54.20 | 200.0 | | | | | **200** |
| **7** | 0.00 | 0.00 | 0.00 | 1.90 | 8.20 | 34.40 | 144.2 | 600.0 | | | | **600** |
| **8** | 0.00 | 0.00 | 0.00 | 1.30 | 4.90 | 17.10 | 60.10 | 212.0 | 750.0 | | | **750** |
| **9** | 0.00 | 0.00 | 0.00 | 1.00 | 3.20 | 9.50 | 30.50 | 92.70 | 290.1 | 900.0 | | **900** |
| **10** | 0.00 | 0.00 | 0.00 | 0.80 | 2.20 | 6.30 | 16.70 | 47.70 | 129.3 | 360.7 | 1000 | **1000** |

Shipped luma-keno Earn `classic` (pins 3–5 and 7 at Off max; pick 6 advertised
80× so 5-of-6 is not a 20× cliff; 8–10 copy Off's climb **750 < 900 < 1000**
so How-to settles 3000 / 3600 / 4000× — was flat 1000× on all three, which
made 8/8 the better jackpot hunt than 10/10 for the same prize):

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.50 | 2.10 | | | | | | | | | | **2.10** |
| **2** | 0.00 | 1.50 | 4.20 | | | | | | | | | **4.20** |
| **3** | 0.00 | 0.30 | 2.70 | 17.50 | | | | | | | | **17.5** |
| **4** | 0.00 | 0.00 | 0.60 | 8.60 | 30.0 | | | | | | | **30** |
| **5** | 0.00 | 0.00 | 1.00 | 2.20 | 10.10 | 75.0 | | | | | | **75** |
| **6** | 0.00 | 0.00 | 1.00 | 1.50 | 3.80 | 11.60 | 80.0 | | | | | **80** |
| **7** | 0.00 | 0.00 | 0.00 | 1.00 | 3.10 | 14.90 | 75.00 | 600.0 | | | | **600** |
| **8** | 0.00 | 0.00 | 0.00 | 1.00 | 2.00 | 6.20 | 18.50 | 93.70 | 750 | | | **750** |
| **9** | 0.00 | 0.00 | 0.00 | 0.00 | 2.00 | 5.80 | 15.90 | 42.30 | 112.50 | 900 | | **900** |
| **10** | 0.00 | 0.00 | 0.00 | 0.70 | 0.90 | 2.30 | 6.00 | 16.00 | 45.00 | 120.00 | 1000 | **1000** |

Pick 8 solved lock-clean from the pin alone (`solve_table`): last catch 8.0×.
Pick 9 pinned as a restair (`restaired_rows.py`): the solver packed its body
at 900 (28.4 → 80 → 118.5, a 1.48× mid pair) but `solve_row`'s uniform
~2.7× ladder is lock-clean at rtp 0.9634; its lock grandfather was dropped.

## Pick 1

Competitor HUD:

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.50x |
| 1 | 2.50x |

Shipped Off `classic` pick_1 advertises **0.40× / 2.60×**. The two-outcome
0.1× lattice cannot reach 0.965 (next point is 0.975, over the 0.967 cap).
Dashboard Cross-Mode includes pick_1, so 6 of 30 miss books pay **0.5×**
(1 in 5 misses). LUT RTP is **0.9650**. Picks 2–10 stay on the 0.9650
geometric ladder.

## Pick 2

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 1.50x |
| 2 | 5.00x |

## Pick 3

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 2.50x |
| 3 | 40.00x |

## Pick 4

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.50x |
| 3 | 9.00x |
| 4 | 100.0x |

## Pick 5

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.10x |
| 3 | 4.00x |
| 4 | 10.00x |
| 5 | 300.0x |

## Pick 6

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 2.00x |
| 4 | 9.00x |
| 5 | 100.0x |
| 6 | 500.0x |

## Pick 7

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.10x |
| 4 | 3.00x |
| 5 | 9.00x |
| 6 | 100.0x |
| 7 | 600.0x |

## Pick 8

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.50x |
| 4 | 3.00x |
| 5 | 9.00x |
| 6 | 40.00x |
| 7 | 200.0x |
| 8 | 750.0x |

## Pick 9

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.10x |
| 4 | 1.50x |
| 5 | 3.00x |
| 6 | 5.00x |
| 7 | 50.00x |
| 8 | 400.0x |
| 9 | 900.0x |

## Pick 10

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.10x |
| 4 | 1.50x |
| 5 | 2.00x |
| 6 | 4.00x |
| 7 | 10.00x |
| 8 | 50.00x |
| 9 | 500.0x |
| 10 | 1000x |

RTP and luma-keno snap: [[sources/keno-xtreme-classic-hud]]. Easy:
[[domain/keno-xtreme-easy]]. Medium: [[domain/keno-xtreme-medium]].
