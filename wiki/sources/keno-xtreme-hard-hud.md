---
type: source
tags: [keno, external-game, stake, paytable, hard, degen]
updated: 2026-09-01
source: Keno Xtreme Hard HUD screenshots (2026-09-01)
---

# Keno Xtreme Hard HUD (pick × hit multipliers)

Live **Hard** paytable from Stake Keno Xtreme (docx name: **Degen**),
transcribed from the in-game HUD. Top = multiplier, bottom `Nx` + gem = hits
`h`. luma-keno risk is **`high`**.

Board: pool **40**, drawn **10**, picks **1–10**. Easy:
[[sources/keno-xtreme-easy-hud]]. Classic: [[sources/keno-xtreme-classic-hud]].
Medium: [[sources/keno-xtreme-medium-hud]].

> Competitor HUD — **not** `paytables.json["risks"]["high"]`.

## Matrix (Hard / Degen)

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.00 | 4.00 | | | | | | | | | | **4** |
| **2** | 0.00 | 0.00 | 20.00 | | | | | | | | | **20** |
| **3** | 0.00 | 0.00 | 0.50 | 500 | | | | | | | | **500** |
| **4** | 0.00 | 0.00 | 0.00 | 1.50 | 1000 | | | | | | | **1000** |
| **5** | 0.00 | 0.00 | 0.00 | 0.50 | 25.00 | 2500 | | | | | | **2500** |
| **6** | 0.00 | 0.00 | 0.00 | 0.25 | 1.50 | 350.0 | 6000 | | | | | **6000** |
| **7** | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 | 3.00 | 950.0 | 12500 | | | | **12500** |
| **8** | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 | 1.50 | 40.00 | 1500 | 25000 | | | **25000** |
| **9** | 0.00 | 0.00 | 0.00 | 0.10 | 0.30 | 0.50 | 5.00 | 40.00 | 3500 | 40000 | | **40000** |
| **10** | 0.00 | 0.00 | 0.00 | 0.10 | 0.30 | 0.50 | 1.50 | 3.00 | 90.00 | 4500 | 50000 | **50000** |

```
k=1  [0.00, 4.00]
k=2  [0.00, 0.00, 20.00]
k=3  [0.00, 0.00, 0.50, 500]
k=4  [0.00, 0.00, 0.00, 1.50, 1000]
k=5  [0.00, 0.00, 0.00, 0.50, 25.00, 2500]
k=6  [0.00, 0.00, 0.00, 0.25, 1.50, 350.0, 6000]
k=7  [0.00, 0.00, 0.00, 0.10, 0.50, 3.00, 950.0, 12500]
k=8  [0.00, 0.00, 0.00, 0.10, 0.50, 1.50, 40.00, 1500, 25000]
k=9  [0.00, 0.00, 0.00, 0.10, 0.30, 0.50, 5.00, 40.00, 3500, 40000]
k=10 [0.00, 0.00, 0.00, 0.10, 0.30, 0.50, 1.50, 3.00, 90.00, 4500, 50000]
```

Max column (picks 1–10): **4 / 20 / 500 / 1000 / 2500 / 6000 / 12500 / 25000 / 40000 / 50000**.

Pick 10 body **0.10 / 0.30 / 0.50 / 1.50 / 3.00 / 90 / 4500 / 50000** matches
keno-math’s Degen row cell-for-cell.

## Per pick (Hard HUD)

### Pick 1

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 4.00x |

### Pick 2

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 20.00x |

### Pick 3

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.50x |
| 3 | 500.0x |

### Pick 4

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.50x |
| 4 | 1000x |

### Pick 5

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.50x |
| 4 | 25.00x |
| 5 | 2500x |

### Pick 6

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.25x |
| 4 | 1.50x |
| 5 | 350.0x |
| 6 | 6000x |

### Pick 7

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.10x |
| 4 | 0.50x |
| 5 | 3.00x |
| 6 | 950.0x |
| 7 | 12500x |

### Pick 8

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.10x |
| 4 | 0.50x |
| 5 | 1.50x |
| 6 | 40.00x |
| 7 | 1500x |
| 8 | 25000x |

### Pick 9

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.10x |
| 4 | 0.30x |
| 5 | 0.50x |
| 6 | 5.00x |
| 7 | 40.00x |
| 8 | 3500x |
| 9 | 40000x |

### Pick 10

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.10x |
| 4 | 0.30x |
| 5 | 0.50x |
| 6 | 1.50x |
| 7 | 3.00x |
| 8 | 90.00x |
| 9 | 4500x |
| 10 | 50000x |

```json
{
  "1": [0.00, 4.00],
  "2": [0.00, 0.00, 20.00],
  "3": [0.00, 0.00, 0.50, 500],
  "4": [0.00, 0.00, 0.00, 1.50, 1000],
  "5": [0.00, 0.00, 0.00, 0.50, 25.00, 2500],
  "6": [0.00, 0.00, 0.00, 0.25, 1.50, 350.0, 6000],
  "7": [0.00, 0.00, 0.00, 0.10, 0.50, 3.00, 950.0, 12500],
  "8": [0.00, 0.00, 0.00, 0.10, 0.50, 1.50, 40.00, 1500, 25000],
  "9": [0.00, 0.00, 0.00, 0.10, 0.30, 0.50, 5.00, 40.00, 3500, 40000],
  "10": [0.00, 0.00, 0.00, 0.10, 0.30, 0.50, 1.50, 3.00, 90.00, 4500, 50000]
}
```

## Shape

- Jackpot-or-bust. Miss-to-1 are dead except pick 1 (`0.00 / 4.00`, same as
  Medium pick 1). Pick 2 pays **only** 2/2. From pick 4 the first paying hit
  is 3; pick 8+ open at **0.10×** on 3 hits (skill already used that).
- Tops climb to **50,000×** on 10/10. That headline is almost free RTP
  (`P(10) ≈ 1.2e-9`).
- Only illegal 0.1× cell: pick 6, 3 hits **0.25×** (25 LUT units). `0.10`
  (10), `0.30` (30), `0.50` (50) are legal.

## Exact RTP (pool 40 / drawn 10)

| k | RTP | house edge |
| ---: | ---: | ---: |
| 1 | 1.000000 | 0.00% |
| 2 | 1.153846 | **−15.38%** |
| 3 | 6.141194 | **−514%** |
| 4 | 2.356932 | **−136%** |
| 5 | 1.236459 | **−23.65%** |
| 6 | 1.085048 | **−8.50%** |
| 7 | 0.459624 | 54.04% |
| 8 | 0.211967 | 78.80% |
| 9 | 0.113489 | 88.65% |
| 10 | 0.109772 | 89.02% |

Picks **2–6 are player-favor** on this HUD. Pick 3’s **500×** alone is
`P(3)×500 ≈ 6.07` RTP (2-Star ETL40 cap 0.80). Do **not** paste 20 / 500 /
1000 / 2500 / 6000 into Off `high`. Picks 8–10 are 11–21% RTP — body cells
(hits 5–9) must fatten to hit the 0.964 fleet; 10/10 can stay 50,000×.

> ⚠️ Contradicts Stake 96.50% page claim even harder than Medium pick 3.
> Small Hard pick sizes cannot ship as-is under 3-Star gates.

## luma-keno mapping

Skill `keno-math` **High (Degen analogue)**:

- Pick 10 HUD is the Degen row. Off pick_10 snap **0.1 / 0.3 / 13.0 / 35.3 /
  137.8 / 808.3 / 7847.9 / 50000** — hits 5–9 fatter; 10/10 ties 50,000×.
- Off/Earn pick_8+ still pay from **3 hits at 0.1×**.
- Pick 1 HUD `0/4` is even money; Off pick_1 stays unpublished.

> ⚠️ Contradicts [[codebase/luma-keno]] shipped Off `high`:
> `paytables.json["risks"]["high"]` is a solver table (pick_2 max **13.4×**,
> pick_3 **64.8×**, pick_10 **4699.8×** not 50,000×). Not this HUD.

## Related

- [[domain/keno-xtreme-hard]]
- [[sources/keno-xtreme-medium-hud]]
- [[codebase/luma-keno]]
- [[domain/stake-rating-limits]]
