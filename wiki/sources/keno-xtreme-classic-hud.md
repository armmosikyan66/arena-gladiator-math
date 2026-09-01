---
type: source
tags: [keno, external-game, stake, paytable, classic]
updated: 2026-09-01
source: Keno Xtreme Classic HUD screenshots (2026-09-01)
---

# Keno Xtreme Classic HUD (pick × hit multipliers)

Live **Classic** paytable from Stake Keno Xtreme (docx name: **Normal**),
transcribed from the in-game HUD. Top row = multiplier, bottom `Nx` + gem =
hit count `h`. Pick size `k` is table width (`k+1` columns).

Board: pool **40**, drawn **10**, picks **1–10**. Hit odds do not change with
risk. Easy HUD: [[sources/keno-xtreme-easy-hud]].

> Competitor HUD — **not** `paytables.json["risks"]["classic"]`. luma-keno
> `classic` is the Normal/Classic analogue; see [[codebase/luma-keno]] and
> skill `keno-math`.

## Matrix (Classic)

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

Copy-paste rows (`pay[h]` for `h = 0..k`):

```
k=1  [0.50, 2.50]
k=2  [0.00, 1.50, 5.00]
k=3  [0.00, 0.00, 2.50, 40.00]
k=4  [0.00, 0.00, 1.50, 9.00, 100.0]
k=5  [0.00, 0.00, 1.10, 4.00, 10.00, 300.0]
k=6  [0.00, 0.00, 0.00, 2.00, 9.00, 100.0, 500.0]
k=7  [0.00, 0.00, 0.00, 1.10, 3.00, 9.00, 100.0, 600.0]
k=8  [0.00, 0.00, 0.00, 1.50, 3.00, 9.00, 40.00, 200.0, 750.0]
k=9  [0.00, 0.00, 0.00, 1.10, 1.50, 3.00, 5.00, 50.00, 400.0, 900.0]
k=10 [0.00, 0.00, 0.00, 1.10, 1.50, 2.00, 4.00, 10.00, 50.00, 500.0, 1000]
```

Max column (picks 1–10): **2.50 / 5.00 / 40 / 100 / 300 / 500 / 600 / 750 / 900 / 1000**.

> ⚠️ keno-math previously listed pick_2 max as **5.3×**. The HUD is **5.00×**.
> Picks 3–10 maxes match the old list (40 / 100 / 300 / 500 / 600 / 750 / 900 / 1000).

## Per pick (Classic HUD)

### Pick 1

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.50x |
| 1 | 2.50x |

### Pick 2

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 1.50x |
| 2 | 5.00x |

### Pick 3

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 2.50x |
| 3 | 40.00x |

### Pick 4

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.50x |
| 3 | 9.00x |
| 4 | 100.0x |

### Pick 5

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.10x |
| 3 | 4.00x |
| 4 | 10.00x |
| 5 | 300.0x |

### Pick 6

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 2.00x |
| 4 | 9.00x |
| 5 | 100.0x |
| 6 | 500.0x |

### Pick 7

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

### Pick 8

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

### Pick 9

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

### Pick 10

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

`paytables.json` shape (do not paste into Off `classic` without retargeting RTP):

```json
{
  "1": [0.50, 2.50],
  "2": [0.00, 1.50, 5.00],
  "3": [0.00, 0.00, 2.50, 40.00],
  "4": [0.00, 0.00, 1.50, 9.00, 100.0],
  "5": [0.00, 0.00, 1.10, 4.00, 10.00, 300.0],
  "6": [0.00, 0.00, 0.00, 2.00, 9.00, 100.0, 500.0],
  "7": [0.00, 0.00, 0.00, 1.10, 3.00, 9.00, 100.0, 600.0],
  "8": [0.00, 0.00, 0.00, 1.50, 3.00, 9.00, 40.00, 200.0, 750.0],
  "9": [0.00, 0.00, 0.00, 1.10, 1.50, 3.00, 5.00, 50.00, 400.0, 900.0],
  "10": [0.00, 0.00, 0.00, 1.10, 1.50, 2.00, 4.00, 10.00, 50.00, 500.0, 1000]
}
```

## Shape

- Steeper than Easy. Pick 1 still pays the miss (`0.50×`). From pick 3 the
  first paying hit is **2**; from pick 6 it is **3**.
- Tops are the marketing ladder: **40 / 100 / 300 / 500 / 600 / 750 / 900 / 1000**.
  Pick 2 top is **5.00×**, not 5.3×.
- Every cell is legal on the Stake 0.1× lattice (`m*100` multiple of 10),
  including `1.10` (110) and `0.50` (50).

## Exact RTP (pool 40 / drawn 10)

`RTP(k) = Σ_h P(h|k) · pay(k,h)` with
`P(h|k) = C(k,h)·C(40−k, 10−h) / C(40,10)`.

| k | RTP | house edge |
| ---: | ---: | ---: |
| 1 | 1.000000 | 0.00% |
| 2 | 0.865385 | 13.46% |
| 3 | 0.827429 | 17.26% |
| 4 | 0.905597 | 9.44% |
| 5 | 0.833379 | 16.66% |
| 6 | 0.692362 | 30.76% |
| 7 | 0.421799 | 57.82% |
| 8 | 0.735093 | 26.49% |
| 9 | 0.553717 | 44.63% |
| 10 | 0.656642 | 34.34% |

Picks 2–10 sit at **42.2–90.6% RTP** (matches the keno-math “42–91%” claim).
Pick 1 is **even money**. Stake’s 96.50% page claim is not this HUD — body
cells on luma-keno Off `classic` have to **rise** to the 0.964 fleet; maxes
can stay.

Pick 7 is the thin row (42.2%). Do not paste this HUD and expect Cross-Mode.

## luma-keno mapping

Skill `keno-math` **Classic (Normal analogue)**: Off `classic` copies **zeros
+ maxes**, then fills the body with a max-anchored geometric ladder onto
0.9650 (`easy_off_classic.py`). Pick 2 HUD **1.50 / 5.00** snaps to **1.7 /
5.4** (5.00 has no in-window lattice point). Pick 10 HUD **1.10 / 1.50 /
2.00 / 4.00 / 10 / 50 / 500 / 1000** becomes **0.8 / 2.2 / 6.3 / 16.7 /
47.7 / 129.3 / 360.7 / 1000** (constant-ratio climb, max stays 1000×).
Earn classic and buy chips keep their own ladders.

Shipped 2026-09-01: `paytables.json["risks"]["classic"]` **is** this chart.

## Related

- [[domain/keno-xtreme-classic]] — per-pick lookup.
- [[sources/keno-xtreme-easy-hud]] — Easy HUD.
- [[sources/keno-xtreme-analysis]]
- [[codebase/luma-keno]]
- [[domain/stake-rating-limits]]
