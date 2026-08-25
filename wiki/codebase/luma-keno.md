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
  `medium` / `high` → **40** modes `{risk}_pick_{k}`.
- Exact hypergeometric LUT weights `C(10,h)·C(30,k-h)`. Skip the Rust
  optimizer.
- **One multiplier per hit count** (0.1× grid). Wallet: sampled book's
  `payoutMultiplier`. Frontend reconstructs the draw from
  `kenoCatch.hits` (skill `keno-math` → events.md).
- Client `MIN_PICKS=1`. Paytable panel: one row per hit, `pay[h]` only.

## Frontend (web)

`web/src/lib/keno/engine.ts` — live `RGSClient` when `sessionID` + `rgs_url`
are on the URL, else a mock that samples the same LUTs
(`web/src/data/keno-books.json`).

`Play({ amount, mode })` with `mode = {risk}_pick_{k}`. Spots are **not** in
the payload. Hits come from `kenoCatch`; `reconstructDraw` invents a 10-ball
board that realizes that hit count. Wallet is `play.balance` (6-decimal
units) — the React store must apply it or the rail never moves.

`planRound` / `settleRound` in `web/src/lib/keno/round.ts` are **preview
only**. Do not use them for certified payout. Buy chips in the UI are not
published modes (still 40 modes, not 80 earn/buy). Mock jurisdiction sets
`disabledBuyFeature: true`.

Keno is single-shot: `auto_close_disabled=False`. Credit on Play; `EndRound`
only if `round.active`.

See client wiki `wiki/codebase/keno-app.md` / `wiki/codebase/rgs-auth.md`.

## RTP

All 40 modes target **0.950** (house edge 5%). pick_1 is lattice-locked
at 0.950 (0.975 busts the 0.967 cap). Picks 2–10 share that target so
dashboard Cross-Mode RTP stays under **0.50pp**. LUT spread ~0.10pp.

Do **not** split miss weight (24+6 remainder). That paid 0.6× and 0.7×
for the same miss on `low_pick_1` and dropped std below the 0.60 floor.

Dashboard gates: hit rate ≥ 2%; Cross-Mode ≤ 0.50pp; per-mode RTP ≤
0.967; Base Mode STD ≥ **0.60** (leave margin — 0.606 displays as 0.60
and fails). local `rgs_verification` only warns at 5pp RTP spread.

pick_1 rows: low **0.5/2.3** (std ~0.78), classic 0.4/2.6, medium 0.2/3.2,
high 0.1/3.5. See [[domain/stake-engine-publish]] and
[[sources/keno-xtreme-analysis]].

## Files

| Path | Owns |
| --- | --- |
| `keno_pick_one.py` | pick_1 lattice (one prize per hit); STD margin |
| `solve_paytables.py` | picks 2–10 solver; `SPREAD_MAX` 0.50pp; RTP 0.950 |
| `paytables.json` | certified tables |
| `run.py` / `export_luts.py` | books, exact weights, `web/src/data/keno-books.json` |

Publish only `library/publish_files/`.

## Related

- [[domain/stake-engine-publish]]
- [[domain/stake-rating-limits]]
- [[codebase/sdk-layout]]
- [[sources/keno-xtreme-analysis]]
