---
type: source
tags: [keno, external-game, stake, paytable, medium]
updated: 2026-09-01
source: Keno Xtreme Medium HUD screenshots (2026-09-01)
---

# Keno Xtreme Medium HUD (pick × hit multipliers)

Live **Medium** paytable from Stake Keno Xtreme (docx name: **Crazy**),
transcribed from the in-game HUD. Top = multiplier, bottom `Nx` + gem = hits
`h`. Pick size `k` is table width.

Board: pool **40**, drawn **10**, picks **1–10**. Easy:
[[sources/keno-xtreme-easy-hud]]. Classic: [[sources/keno-xtreme-classic-hud]].

> Competitor HUD — **not** `paytables.json["risks"]["medium"]`. luma-keno
> `medium` is the Crazy/Medium analogue; see [[codebase/luma-keno]].

## Matrix (Medium)

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.00 | 4.00 | | | | | | | | | | **4.00** |
| **2** | 0.00 | 0.95 | 9.00 | | | | | | | | | **9.00** |
| **3** | 0.00 | 0.00 | 1.75 | 75.00 | | | | | | | | **75.00** |
| **4** | 0.00 | 0.00 | 0.95 | 7.00 | 175.0 | | | | | | | **175.0** |
| **5** | 0.00 | 0.00 | 1.20 | 3.00 | 9.00 | 450.0 | | | | | | **450.0** |
| **6** | 0.00 | 0.00 | 0.00 | 1.50 | 5.00 | 50.00 | 650.0 | | | | | **650.0** |
| **7** | 0.00 | 0.00 | 0.00 | 0.95 | 3.00 | 7.50 | 90.00 | 750.0 | | | | **750.0** |
| **8** | 0.00 | 0.00 | 0.00 | 0.95 | 2.00 | 5.00 | 15.00 | 150.0 | 2500 | | | **2500** |
| **9** | 0.00 | 0.00 | 0.00 | 0.95 | 1.10 | 2.50 | 5.00 | 40.00 | 350.0 | 4000 | | **4000** |
| **10** | 0.00 | 0.00 | 0.00 | 0.50 | 0.95 | 1.50 | 3.00 | 9.00 | 40.00 | 400.0 | 5000 | **5000** |

```
k=1  [0.00, 4.00]
k=2  [0.00, 0.95, 9.00]
k=3  [0.00, 0.00, 1.75, 75.00]
k=4  [0.00, 0.00, 0.95, 7.00, 175.0]
k=5  [0.00, 0.00, 1.20, 3.00, 9.00, 450.0]
k=6  [0.00, 0.00, 0.00, 1.50, 5.00, 50.00, 650.0]
k=7  [0.00, 0.00, 0.00, 0.95, 3.00, 7.50, 90.00, 750.0]
k=8  [0.00, 0.00, 0.00, 0.95, 2.00, 5.00, 15.00, 150.0, 2500]
k=9  [0.00, 0.00, 0.00, 0.95, 1.10, 2.50, 5.00, 40.00, 350.0, 4000]
k=10 [0.00, 0.00, 0.00, 0.50, 0.95, 1.50, 3.00, 9.00, 40.00, 400.0, 5000]
```

Max column (picks 1–10): **4 / 9.00 / 75 / 175 / 450 / 650 / 750 / 2500 / 4000 / 5000**.

> ⚠️ keno-math listed pick_2 max **9.3×** and pick_3 max **65.8×**. HUD is
> **9.00×** and **75.00×**. 75× on pick 3 is why that row is >100% RTP and
> fails 2-Star ETL40 — luma-keno must not copy 75×.

## Per pick (Medium HUD)

### Pick 1

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 4.00x |

### Pick 2

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.95x |
| 2 | 9.00x |

### Pick 3

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.75x |
| 3 | 75.00x |

### Pick 4

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.95x |
| 3 | 7.00x |
| 4 | 175.0x |

### Pick 5

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.20x |
| 3 | 3.00x |
| 4 | 9.00x |
| 5 | 450.0x |

### Pick 6

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.50x |
| 4 | 5.00x |
| 5 | 50.00x |
| 6 | 650.0x |

### Pick 7

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.95x |
| 4 | 3.00x |
| 5 | 7.50x |
| 6 | 90.00x |
| 7 | 750.0x |

### Pick 8

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.95x |
| 4 | 2.00x |
| 5 | 5.00x |
| 6 | 15.00x |
| 7 | 150.0x |
| 8 | 2500x |

### Pick 9

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.95x |
| 4 | 1.10x |
| 5 | 2.50x |
| 6 | 5.00x |
| 7 | 40.00x |
| 8 | 350.0x |
| 9 | 4000x |

### Pick 10

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 0.50x |
| 4 | 0.95x |
| 5 | 1.50x |
| 6 | 3.00x |
| 7 | 9.00x |
| 8 | 40.00x |
| 9 | 400.0x |
| 10 | 5000x |

```json
{
  "1": [0.00, 4.00],
  "2": [0.00, 0.95, 9.00],
  "3": [0.00, 0.00, 1.75, 75.00],
  "4": [0.00, 0.00, 0.95, 7.00, 175.0],
  "5": [0.00, 0.00, 1.20, 3.00, 9.00, 450.0],
  "6": [0.00, 0.00, 0.00, 1.50, 5.00, 50.00, 650.0],
  "7": [0.00, 0.00, 0.00, 0.95, 3.00, 7.50, 90.00, 750.0],
  "8": [0.00, 0.00, 0.00, 0.95, 2.00, 5.00, 15.00, 150.0, 2500],
  "9": [0.00, 0.00, 0.00, 0.95, 1.10, 2.50, 5.00, 40.00, 350.0, 4000],
  "10": [0.00, 0.00, 0.00, 0.50, 0.95, 1.50, 3.00, 9.00, 40.00, 400.0, 5000]
}
```

## Shape

- Jackpot-shaped vs Easy/Classic. Pick 1 pays **nothing on a miss** (`0.00 /
  4.00`). First paying hit is often a **partial** (`0.95`, `0.50`).
- Tops: **9 / 75 / 175 / 450 / 650 / 750 / 2500 / 4000 / 5000**.
- `0.95×` is illegal on the Stake 0.1× lattice (95 LUT units). Snap to
  **1.0×**. `1.75×` (pick 3, 2 hits) is also illegal (175).

## Exact RTP (pool 40 / drawn 10)

| k | RTP | house edge |
| ---: | ---: | ---: |
| 1 | 1.000000 | 0.00% |
| 2 | 0.884615 | 11.54% |
| 3 | 1.150051 | **−15.01%** (player-favor) |
| 4 | 0.881346 | 11.87% |
| 5 | 0.829686 | 17.03% |
| 6 | 0.443429 | 55.66% |
| 7 | 0.384107 | 61.59% |
| 8 | 0.453732 | 54.63% |
| 9 | 0.456182 | 54.38% |
| 10 | 0.374007 | 62.60% |

Pick 3 is **115% RTP** because `P(3|k=3)×75 ≈ 0.911` (over the 2-Star ETL40
0.80 cap). Skill snap: pick 3 max **65.8×** (`P×65.8 ≈ 0.799`), not 75×.
Picks 6–10 sit at **37–46% RTP** — body cells must rise for the 0.964 fleet.
Pick 1 is even money.

## Illegal on the 0.1× lattice

| k | h | HUD | LUT units |
| ---: | ---: | ---: | ---: |
| 2 | 1 | 0.95 | 95 |
| 3 | 2 | 1.75 | 175 |
| 4 | 2 | 0.95 | 95 |
| 7 | 3 | 0.95 | 95 |
| 8 | 3 | 0.95 | 95 |
| 9 | 3 | 0.95 | 95 |
| 10 | 4 | 0.95 | 95 |

Legal look-alikes: `1.10` (110), `1.20` (120), `7.50` (750), `0.50` (50).

## luma-keno mapping

Skill `keno-math` **Medium (Crazy analogue)**: copy **shape + maxes except
pick 3**, snap `0.95→1.0`, retarget body RTP.

- Pick 2 HUD **0.95 / 9.00**. Max stays **9.00×**, not 9.3×. `0.95→1.0`.
- Pick 3 HUD **1.75 / 75**. Do **not** ship 75×. Cap **65.8×** (ETL40).
- Pick 10 HUD **0.50 / 0.95 / 1.50 / 3.00 / 9 / 40 / 400 / 5000**. Skill snap
  **1.8 / 2.1 / 2.5 / 3.5 / 9 / 40 / 400 / 5000** (start at 4 so Earn
  Lumen/Pulse do not settle a 0.5× 3-hit).
- Earn/Buy still start paying at 4 hits for that reason.

> ⚠️ Contradicts [[codebase/luma-keno]] shipped Off `medium`:
> `paytables.json["risks"]["medium"]` is a solver table (pick_2 max **3.4×**,
> pick_3 **61.5×**, pick_10 **1500×**). Not this HUD.

## Related

- [[domain/keno-xtreme-medium]]
- [[sources/keno-xtreme-classic-hud]]
- [[sources/keno-xtreme-easy-hud]]
- [[codebase/luma-keno]]
- [[domain/stake-rating-limits]]
