---
type: source
tags: [keno, external-game, stake, probability, rtp]
updated: 2026-09-01
source_file: math/wiki/sources/keno_xtreme_probability_analysis.docx
---

# Keno Xtreme probability analysis (external docx)

External analysis of Stake Keno Xtreme (Degen Lab) provided as a .docx in
`math/wiki/sources/`. Numbers below are what the document claims about the
**competitor** game; luma-keno comparisons are ours.

## Structure (per the docx)

- Board 40 numbers, player picks 1–10, draw 10.
- Five volatility modes: Easy, Normal, Crazy, Xtreme, Degen.
- Stake page shows 3.50% house edge (96.50% RTP).
- Hit probability per (picks p, hits k):
  `P(k|p) = C(p,k)·C(40−p, 10−k) / C(40,10)` — hypergeometric, identical
  across volatility modes; only the multiplier table changes.
- Max-win claims for Keno Xtreme: 50,000×–100,000× (third-party listings,
  inconsistent between sources).
- **The docx contains no multiplier values** — every cell is marked
  "VERIFY IN GAME" because the live Stake page doesn't expose the payout
  matrix in crawlable text.
- **Easy HUD is now transcribed** from in-game screenshots (2026-08-31):
  [[sources/keno-xtreme-easy-hud]]. Pick 1–10 matrices, maxes
  **2 / 4.5 / 10.4 / 22.5 / 36 / 40 / 60 / 70 / 85 / 100**, RTP ~99.0%
  except pick 9 (~97.7%). That **contradicts** the 96.50% page claim for
  Easy alone; other volatility modes are what create the marketed edge.
- **Classic HUD is now transcribed** from in-game screenshots (2026-09-01):
  [[sources/keno-xtreme-classic-hud]] / [[domain/keno-xtreme-classic]].
  Maxes **2.50 / 5.00 / 40 / 100 / 300 / 500 / 600 / 750 / 900 / 1000**.
  Picks 2–10 RTP **42.2–90.6%**; pick 1 is even money. Pick 2 max is
  **5.00×**, not 5.3×.
- **Medium HUD is now transcribed** from in-game screenshots (2026-09-01):
  [[sources/keno-xtreme-medium-hud]] / [[domain/keno-xtreme-medium]].
  Maxes **4 / 9.00 / 75 / 175 / 450 / 650 / 750 / 2500 / 4000 / 5000**.
  Pick 3 at **75× is 115% RTP** (ETL40 fail — luma-keno uses 65.8×).
  `0.95×` is illegal on the 0.1× lattice. Pick 2 max is **9.00×**, not 9.3×.
- **Hard HUD is now transcribed** from in-game screenshots (2026-09-01):
  [[sources/keno-xtreme-hard-hud]] / [[domain/keno-xtreme-hard]]. Docx name
  **Degen**. Maxes **4 / 20 / 500 / 1000 / 2500 / 6000 / 12500 / 25000 /
  40000 / 50000**. Pick 10 body matches Degen. Picks 2–6 are player-favor
  (pick 3 ~614% RTP at 500×). Only illegal cell: pick 6 `0.25×`.

## Verification against luma-keno (2026-08-25)

Diffed every docx probability table against
`games/luma-keno/game_calculations.hit_weight` (pool 40 / drawn 10):

- k=1: max diff `0.00e+00`; k=5: `3.68e-11`; k=10: `1.17e-07`
  (pure print-rounding). **Probability side is identical and exact.**

Differences vs our game:

| | Keno Xtreme (docx) | luma-keno |
| --- | --- | --- |
| Picks | 1–10 | **1–10** |
| Risk modes | 5 | 4 (classic/low/medium/high) |
| RTP | 96.50% | **95.00%** all 40 modes (Cross-Mode ≤ 0.50pp; pick_1 lattice) |
| Top prize | 50k–100k× (claims) | 800/400/1500/4900× by risk (CVaR/ETL-bound) |

## Best practice confirmed by the docx

- Verify RTP independently per pick count and mode:
  `RTP(p,mode) = Σ P(k|p)·mult(p,mode,k)` — exactly what
  `solve_paytables.py` → `mode_stats`/`check_gates` does.
- One shared probability table across volatility modes — our 4 risks share
  the exact hypergeometric LUT weights.
- Don't mix boost/buy features into base-round RTP — luma-keno extras
  (Lumen/Pulse/buy) are preview-only and excluded from wallet math.

## Low-hit refunds (Stake Originals style, 2026-08-25)

Keno Xtreme's public page does not expose multipliers, but Stake Originals
Keno (same 40/10 board) uses a **volatility-shaped paytable**, not a
separate "refund mechanic":
- Low/Classic pay small amounts on low hit counts ("gentle bleed").
- High pays nothing until 3–4 hits (jackpot-or-bust).
- Same RTP every mode; only the ladder shape changes.

luma-keno now does the same on the certified 0.1× grid:
- `classic`/`low` only: a **fixed 0.5×** (50 LUT units — legal: multiple
  of 10) one hit below the pay start, when `P(h) ≤ 0.35`.
- classic `pick_10` pay-start moved to 4 hits so the refund lands on
  **3 hits** (the example the player asked for).
- `medium`/`high` stay jackpot-shaped (no refund).
- Stake's 0.25× is illegal on our RGS (25 is not a multiple of 10).
- pick_2/3 have no tier below start; classic pick_4 / low pick_5–6 skip
  the refund because P(h) is too high (~0.37–0.44) and would eat the RTP
  budget.

## pick_1 lattice (2026-08-25)

`verify_mode_volatility` caps per-mode RTP at **0.967**. pick_1 is a
two-outcome game on the 0.1× payout grid with P(hit)=0.25, so a single
miss/hit pair has RTP in steps of **0.025**. The lattice jumps 0.95 →
0.975; 0.975 busts the ceiling.

A miss remainder (split weight 24+6 so some misses pay +0.1×) lifts LUT
RTP to 0.965 but pays **two prizes for one miss** (history 0.6× vs 0.7×)
and drops low_pick_1 std onto/below the 0.60 floor. **Do not use it.**

Current tables (`keno_pick_one.py`): one miss/hit pair at 0.950 — low
**0.5/2.3** (std ~0.78), classic 0.4/2.6, medium 0.2/3.2, high 0.1/3.5.
Picks 2–10 share 0.950. LUT weights 30 + 10. Client `MIN_PICKS=1`. One
row per hit count.

## Related

- [[sources/keno-xtreme-easy-hud]] — Easy HUD multipliers (screenshots 2026-08-31).
- [[sources/keno-xtreme-classic-hud]] — Classic HUD multipliers (screenshots 2026-09-01).
- [[sources/keno-xtreme-medium-hud]] — Medium HUD multipliers (screenshots 2026-09-01).
- [[sources/keno-xtreme-hard-hud]] — Hard / Degen HUD multipliers (screenshots 2026-09-01).
- [[domain/keno-xtreme-classic]]
- [[domain/keno-xtreme-medium]]
- [[domain/keno-xtreme-hard]]
- [[domain/stake-rating-limits]] — the 0.967 ceiling and 3-Star gates.
- [[codebase/luma-keno]]
