---
type: source
tags: [keno, external-game, stake, probability, rtp]
updated: 2026-08-25
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

## Verification against luma-keno (2026-08-25)

Diffed every docx probability table against
`games/luma-keno/game_calculations.hit_weight` (pool 40 / drawn 10):

- k=1: max diff `0.00e+00`; k=5: `3.68e-11`; k=10: `1.17e-07`
  (pure print-rounding). **Probability side is identical and exact.**

Differences vs our game:

| | Keno Xtreme (docx) | luma-keno |
| --- | --- | --- |
| Picks | 1–10 | **1–10** (pick_1 LUT RTP 0.965 via miss remainder; see below) |
| Risk modes | 5 | 4 (classic/low/medium/high) |
| RTP | 96.50% | **~96.60%** (target 0.9660, realized 0.9650–0.9665) |
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

## pick_1 at ~96.6% (lattice remainder, 2026-08-25)

`verify_mode_volatility` caps per-mode RTP at **0.967**. pick_1 is a
two-outcome game on the 0.1× payout grid with P(hit)=0.25, so a single
miss/hit pair has RTP in steps of **0.025**. The lattice jumps 0.95 →
0.975; 0.975 busts the ceiling. Keeping advertised pick_1 at 0.95 next to
picks 2–10 at 0.9660 is a **1.65pp** spread — legal for `rgs_verification`
(5pp) but blocked by the dashboard Cross-Mode RTP gate (**0.50pp**).

A single advertised pair cannot land on 96.6%. luma-keno keeps the
advertised 0.950 miss/hit row (per-risk shape: low 0.6/2.0, classic
0.4/2.6, medium 0.2/3.2, high 0.1/3.5) and splits miss weight
`C(10,0)·C(30,1)=30` into **24 @ advertised miss** and **6 @ miss+0.1×**.
Hit weight stays exact 10/40. LUT RTP is **0.965**. Spread vs max pick
2–10 (0.9665) is **0.15pp**. Match prize is deterministic vs the
paytable; the extra 0.1× is player-favorable on 20% of misses
(`keno_pick_one.py`). Do not map pick_1 onto pick_2 books.

## Related

- [[domain/stake-rating-limits]] — the 0.967 ceiling and 3-Star gates.
- [[codebase/luma-keno]] ? (page not yet created)
