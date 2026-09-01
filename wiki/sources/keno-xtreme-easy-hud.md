---
type: source
tags: [keno, external-game, stake, paytable, easy]
updated: 2026-09-01
source: Keno Xtreme Easy HUD screenshots (2026-08-31)
---

# Keno Xtreme Easy HUD (pick × hit multipliers)

Live **Easy** paytable from Stake Keno Xtreme, transcribed from the in-game
HUD (top row = `payoutMultiplier`, bottom row = hit count `h` plus gem icon).
Pick size `k` is the table width: `k+1` columns, `h = 0..k`.

Board is the same as luma-keno: pool **40**, drawn **10**, picks **1–10**.
Hit odds are hypergeometric and **do not change with risk** — only this
multiplier matrix is Easy-specific.

> This page is the competitor HUD. It is **not** `paytables.json["risks"]["low"]`.
> luma-keno `low` is the Easy analogue; see [[codebase/luma-keno]] and skill
> `keno-math`. Earlier [[sources/keno-xtreme-analysis]] had no multipliers
> (docx cells were "VERIFY IN GAME").

## How to read the HUD

- Bottom `Nx` + hexagon = **hits** `h`, not the player's pick count.
- Top `M.xx` = advertised multiplier for that hit count.
- `0.00x` is a dead row (stake lost). Non-zero below `1.00x` is a partial
  return, not a win in the hit-rate sense.

## Matrix (Easy)

Empty cells are impossible (`h > k`). Values are exact HUD strings.

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.65 | 2.00 | | | | | | | | | | **2.00** |
| **2** | 0.00 | 1.90 | 4.50 | | | | | | | | | **4.50** |
| **3** | 0.00 | 1.00 | 3.10 | 10.40 | | | | | | | | **10.40** |
| **4** | 0.00 | 0.80 | 1.80 | 5.00 | 22.50 | | | | | | | **22.50** |
| **5** | 0.00 | 0.25 | 1.40 | 4.10 | 16.50 | 36.00 | | | | | | **36.00** |
| **6** | 0.00 | 0.00 | 1.00 | 3.68 | 7.00 | 16.50 | 40.00 | | | | | **40.00** |
| **7** | 0.00 | 0.00 | 0.47 | 3.00 | 4.50 | 14.00 | 31.00 | 60.00 | | | | **60.00** |
| **8** | 0.00 | 0.00 | 0.00 | 2.20 | 4.00 | 13.00 | 22.00 | 55.00 | 70.00 | | | **70.00** |
| **9** | 0.00 | 0.00 | 0.00 | 1.50 | 3.00 | 8.00 | 15.00 | 44.00 | 60.00 | 85.00 | | **85.00** |
| **10** | 0.00 | 0.00 | 0.00 | 1.40 | 2.25 | 4.50 | 8.00 | 17.00 | 50.00 | 80.00 | 100.0 | **100.0** |

Copy-paste rows (`pay[h]` for `h = 0..k`):

```
k=1  [0.65, 2.00]
k=2  [0.00, 1.90, 4.50]
k=3  [0.00, 1.00, 3.10, 10.40]
k=4  [0.00, 0.80, 1.80, 5.00, 22.50]
k=5  [0.00, 0.25, 1.40, 4.10, 16.50, 36.00]
k=6  [0.00, 0.00, 1.00, 3.68, 7.00, 16.50, 40.00]
k=7  [0.00, 0.00, 0.47, 3.00, 4.50, 14.00, 31.00, 60.00]
k=8  [0.00, 0.00, 0.00, 2.20, 4.00, 13.00, 22.00, 55.00, 70.00]
k=9  [0.00, 0.00, 0.00, 1.50, 3.00, 8.00, 15.00, 44.00, 60.00, 85.00]
k=10 [0.00, 0.00, 0.00, 1.40, 2.25, 4.50, 8.00, 17.00, 50.00, 80.00, 100.0]
```

Max column (picks 1–10): **2.00 / 4.50 / 10.40 / 22.50 / 36 / 40 / 60 / 70 / 85 / 100**.

## Per pick (Easy HUD)

Same cells as the matrix, one table per pick size — this is how the in-game
HUD is laid out (top = multiplier, bottom = hits).

### Pick 1

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.65x |
| 1 | 2.00x |

### Pick 2

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 1.90x |
| 2 | 4.50x |

### Pick 3

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 1.00x |
| 2 | 3.10x |
| 3 | 10.40x |

### Pick 4

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.80x |
| 2 | 1.80x |
| 3 | 5.00x |
| 4 | 22.50x |

### Pick 5

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.25x |
| 2 | 1.40x |
| 3 | 4.10x |
| 4 | 16.50x |
| 5 | 36.00x |

### Pick 6

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 1.00x |
| 3 | 3.68x |
| 4 | 7.00x |
| 5 | 16.50x |
| 6 | 40.00x |

### Pick 7

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.47x |
| 3 | 3.00x |
| 4 | 4.50x |
| 5 | 14.00x |
| 6 | 31.00x |
| 7 | 60.00x |

### Pick 8

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 2.20x |
| 4 | 4.00x |
| 5 | 13.00x |
| 6 | 22.00x |
| 7 | 55.00x |
| 8 | 70.00x |

### Pick 9

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.50x |
| 4 | 3.00x |
| 5 | 8.00x |
| 6 | 15.00x |
| 7 | 44.00x |
| 8 | 60.00x |
| 9 | 85.00x |

### Pick 10

| Hits | Multiplier |
| ---: | ---: |
| 0 | 0.00x |
| 1 | 0.00x |
| 2 | 0.00x |
| 3 | 1.40x |
| 4 | 2.25x |
| 5 | 4.50x |
| 6 | 8.00x |
| 7 | 17.00x |
| 8 | 50.00x |
| 9 | 80.00x |
| 10 | 100.0x |

`paytables.json` shape (`"low"` analogue — **do not paste into Off low
without the 0.1× snap**):

```json
{
  "1": [0.65, 2.00],
  "2": [0.00, 1.90, 4.50],
  "3": [0.00, 1.00, 3.10, 10.40],
  "4": [0.00, 0.80, 1.80, 5.00, 22.50],
  "5": [0.00, 0.25, 1.40, 4.10, 16.50, 36.00],
  "6": [0.00, 0.00, 1.00, 3.68, 7.00, 16.50, 40.00],
  "7": [0.00, 0.00, 0.47, 3.00, 4.50, 14.00, 31.00, 60.00],
  "8": [0.00, 0.00, 0.00, 2.20, 4.00, 13.00, 22.00, 55.00, 70.00],
  "9": [0.00, 0.00, 0.00, 1.50, 3.00, 8.00, 15.00, 44.00, 60.00, 85.00],
  "10": [0.00, 0.00, 0.00, 1.40, 2.25, 4.50, 8.00, 17.00, 50.00, 80.00, 100.0]
}
```

## Shape

- **Gentle bleed.** Small `k` pays from 0–1 hits. From `k=6` the first
  paying hit moves out: miss-to-1 are dead, then miss-to-2 from `k=8`.
- **Partial returns** on the first paying hit for several sizes (`0.65`,
  `0.80`, `0.25`, `0.47`) — same idea as Stake Originals Low, not a
  separate refund mechanic.
- Tops stay modest. Easy pick_10 max is **100×**, not 400× / 1000× /
  50,000×. Do not "fix" 70 / 85 / 100 up to a solver `top`.

## Exact RTP (pool 40 / drawn 10)

`RTP(k) = Σ_h P(h|k) · pay(k,h)` with
`P(h|k) = C(k,h)·C(40−k, 10−h) / C(40,10)`.

| k | RTP | house edge |
| ---: | ---: | ---: |
| 1 | 0.987500 | 1.25% |
| 2 | 0.990385 | 0.96% |
| 3 | 0.990182 | 0.98% |
| 4 | 0.989605 | 1.04% |
| 5 | 0.989858 | 1.01% |
| 6 | 0.989665 | 1.03% |
| 7 | 0.989815 | 1.02% |
| 8 | 0.990228 | 0.98% |
| 9 | 0.976724 | 2.33% |
| 10 | 0.990374 | 0.96% |

Picks 1–8 and 10 sit at **~99.0% RTP** (~1% edge). Pick 9 is **~1.3pp
lower** on the transcribed cells (mid-hits thinner than pick 8). Stake's
marketing page still claims 96.50% / 3.50% edge for the game as a whole —
this Easy HUD does not match that claim.

> ⚠️ Contradicts Stake page 96.50% RTP and [[sources/keno-xtreme-analysis]]
> "3.50% house edge": Easy alone is ~99% except pick 9. Other volatility
> modes (Normal / Crazy / Degen) are what pull the blended edge down.
> luma-keno targets **0.964–0.965** every risk, so Off `low` cannot paste
> this HUD and pass Cross-Mode.

## Illegal on the Stake Engine 0.1× lattice

`payoutMultiplier = int(round(m * 100))` must be a multiple of 10.
These Easy cells cannot ship as-is:

| k | h | HUD | LUT units | problem |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | 0.65 | 65 | not ×10 |
| 5 | 1 | 0.25 | 25 | not ×10 (wiki already flagged Stake Originals 0.25×) |
| 6 | 3 | 3.68 | 368 | not ×10 |
| 7 | 2 | 0.47 | 47 | not ×10 |
| 10 | 4 | 2.25 | 225 | not ×10 |

Legal HUD cells that look "off-grid" but are fine: `0.80` (80), `1.90`
(190), `2.20` (220), `4.50` (450), `10.40` (1040), `16.50` (1650),
`22.50` (2250).

## luma-keno mapping (do not paste blindly)

Skill `keno-math` **Low (Easy analogue)**: Off `low` copies this HUD's
**shape and maxes**, then:

- Snap illegal cells onto 0.1× (`0.47→0.4`, `2.25→2.1`, `3.68→…`).
- Pick 2 HUD `1.90 / 4.50` is **0.990 RTP**. `1.8 / 4.5` is 0.952; the
  skill's published snap is **1.8 / 4.7** so the max moves 4.50→4.7 and
  RTP lands near the 0.964 fleet. **Do not keep 4.50 if you drop 1.90.**
- Pick 7 snap in the skill: **0.4 / 3.0 / 4.4 / 14.4 / 31 / 60** (HUD
  `0.47 / 3.00 / 4.50 / 14.00 / 31.00 / 60.00`).
- Pick 10 snap in the skill: **1.4 / 2.1 / 4.4 / 8 / 17 / 50 / 80 / 100**
  (HUD `1.40 / 2.25 / 4.50 / 8.00 / 17.00 / 50.00 / 80.00 / 100.0`).
- Earn/buy keep their own ladders (Earn low pick_8–10 advertise 100× so
  Lumen×2 × Pulse×2 can settle 400×). Off must **not** replace Easy
  70/85/100 with the solver `top` of 400×.

> ⚠️ ~~Contradicts [[codebase/luma-keno]] shipped Off `low`~~ **Resolved
> 2026-09-01**: `paytables.json["risks"]["low"]` is now this HUD's snapped
> copy (`easy_off_low.py`) — picks 2/7/10 use the snaps below verbatim;
> 3/4/5/6/8/9 were derived under the same rules. Earn/buy `low` ladders are
> unchanged and keep their own ladders (Earn low pick_8–10 advertise 100× so
> Lumen×2 × Pulse×2 settles 400×). Off does **not** replace Easy 70/85/100
> with the solver `top` of 400×.

## Related

- [[sources/keno-xtreme-analysis]] — probabilities, 5-mode structure, no
  multipliers until this ingest.
- [[domain/keno-xtreme-easy]] — per-pick lookup tables (same cells).
- [[sources/keno-xtreme-classic-hud]] — Classic HUD.
- [[codebase/luma-keno]] — our `low` risk.
- [[domain/stake-rating-limits]] — 0.1× lattice, Cross-Mode 0.50pp, 0.967 cap.
