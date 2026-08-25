---
type: codebase
tags: [keno, luma-keno, rtp, publish]
updated: 2026-08-25
---

# Luma Keno math

Hit-count keno in `math/games/luma-keno/`. `win_type = "other"`. Skill
`keno-math`. Not a slot and not Tower.

## Contract

- Pool **40**, drawn **10**, picks **1–10**, risks `classic` / `low` /
  `medium` / `high`.
- **80** modes, both `cost=1.0`, `is_buybonus=False`:
  - Off `{risk}_pick_{k}` — table only. Weights `C(10,h)·C(30,k-h)`.
    `paytables.json["risks"]`. `lumenMarked=false`.
  - Earn `{risk}_pick_{k}_earn` — Lumen + extras + Pulse ×2 (10%) priced into
    `paytables.json["earn"]`.
- Skip the Rust optimizer. Exact hypergeometric (and Earn extra-open)
  weights.
- Wallet: sampled book's `payoutMultiplier` (Earn already includes
  Lumen; the client does not re-multiply). Frontend reconstructs the
  main ten from `kenoCatch.mainHits`. Earn also reconstructs Lumen from
  `lumenHit` and extras from `extraHits` (skill `keno-math` → events.md).
- Client `MIN_PICKS=1`. Paytable panel follows the sidebar chart.

## Off vs Earn

Sidebar **Off** is the certified 0.950 table with no bonuses. Sidebar
**Earn** is a separate 0.950 chart so Lumen and extras do not inflate
Off RTP.

Earn Lumen: always one of the main 10. Catching on a paying row
multiplies by `LUMEN_BOOST` — classic/low/**medium ×2**, high ×5.
Medium is ×2 (not ×3) so Earn pick_1 stays on the 0.1× lattice inside
0.50pp of Off. Lumen does **not** rescue a 0× row.

Earn extras: 0 or 2 from the remaining 30 (`lumen` / `nearMiss` / luck).
Extra hits pay the Earn table, then Lumen multiplies that base.

Earn Pulse: **10%** of rounds apply ×2 after Lumen, only on a paying
table. Independent of extras.

Pulse and Buy chips: Pulse is now booked math. Buy is still UI-only.

## Frontend (web)

`web/src/lib/keno/engine.ts` — live `RGSClient` when `sessionID` + `rgs_url`
are on the URL, else a mock that samples the same LUTs
(`web/src/data/keno-books.json`).

`Play({ amount, mode })` with `mode = {risk}_pick_{k}` or
`{risk}_pick_{k}_earn` from the Off/Earn sidebar. Spots are **not** in
the payload. Hits come from `kenoCatch`; `reconstructDraw` invents a
10-ball main board from `mainHits`. Off: no marked light, no extras.
Earn: extras after a pause if booked; Lumen marked before the first
reveal. Wallet is `play.balance`.

`planRound` / `settleRound` in `web/src/lib/keno/round.ts` are **preview
only**. Do not use them for certified payout. Mock jurisdiction sets
`disabledBuyFeature: true`.

Keno is single-shot: `auto_close_disabled=False`. Credit on Play; `EndRound`
only if `round.active`.

See client wiki `wiki/codebase/keno-app.md` / `wiki/codebase/rgs-auth.md`.

## RTP

All 80 modes **target** **0.950** (house edge 5%). Off pick_1 is
lattice-locked at 0.950 (classic 0.4/2.6, low 0.5/2.3, medium 0.2/3.2,
high 0.1/3.5). Earn pick_1 uses a different pair (classic **0.2/2.9**,
settled ~0.9475 after Lumen) so Cross-Mode across 80 modes stays
≤ 0.50pp.

Do **not** split miss weight (24+6 remainder). That paid 0.6× and 0.7×
for the same miss on `low_pick_1` and dropped std below the 0.60 floor.

Dashboard gates: hit rate ≥ 2%; Cross-Mode ≤ **0.50pp** over all 80
modes; per-mode RTP ≤ 0.967; Base Mode STD ≥ **0.60** (leave margin —
0.606 displays as 0.60 and fails). local `rgs_verification` only warns
at 5pp RTP spread. Treat warnings as failures.

See [[domain/stake-engine-publish]] and [[sources/keno-xtreme-analysis]].

## Files

| Path | Owns |
| --- | --- |
| `keno_pick_one.py` | Off + Earn pick_1 lattices; lumen/extra criteria; `lumen_pay` |
| `solve_paytables.py` | Off tables unchanged; Earn solver with bonuses priced in |
| `paytables.json` | `risks` (Off) + `earn` |
| `run.py` / `export_luts.py` | 80-mode books; Off hypergeometric; Earn lumen×extra weights; `web/src/data/keno-books.json` |

Publish only `library/publish_files/`.

## Related

- Skill `keno-math`
- [[domain/stake-engine-publish]]
- [[sources/keno-xtreme-analysis]]
