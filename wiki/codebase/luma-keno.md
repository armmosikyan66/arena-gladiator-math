---
type: codebase
tags: [keno, luma-keno, rtp, publish, telemetry]
updated: 2026-08-28
---

# Luma Keno math

Hit-count keno in `math/games/luma-keno/`. `win_type = "other"`. Skill
`keno-math`. Not a slot and not Tower.

## Contract

- Pool **40**, drawn **10**, picks **1–10**, risks `classic` / `low` /
  `medium` / `high`.
- **160** modes:
  - Off `{risk}_pick_{k}` — table only, `cost=1.0`, `is_buybonus=False`. Weights
    `C(10,h)·C(30,k-h)`. `paytables.json["risks"]`. `lumenMarked=false`.
  - Earn `{risk}_pick_{k}_earn` — `cost=1.0`, `is_buybonus=False`. Lumen +
    extras + Pulse (10%) priced into `paytables.json["earn"]`.
  - Buy `{risk}_pick_{k}_buy10` / `_buy100` — `cost=10.0` / `100.0`,
    `is_buybonus=True`. Earn rules with the extras forced open.
    `paytables.json["buy10"]` / `["buy100"]`. Certified 2026-08-28; see
    **Buy chips** below.
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
multiplies by `LUMEN_BOOST` — **×2 on every risk**, and the same boost applies
on both buy chips. Lumen does **not** rescue a 0× row.

> ⚠️ This page said high was ×5 until 2026-08-28. At ×5 it carried 67–74% of the
> return on picks 5–10 through a channel paying on ~2.6% of rounds, leaving the
> base table at ~14%; the re-solve dropped it to ×2.

Earn extras: 0 or 2 from the remaining 30 (`lumen` / `nearMiss` / luck).
Extra hits pay the Earn table, then Lumen multiplies that base.

Earn Pulse: **10%** of rounds roll Pulse and apply it after Lumen, only
on a paying table. Independent of extras. Boost is ×2 on
classic/low/high and **×3 on medium**.

> ⚠️ This page said "×2" uniformly until 2026-08-28. `f506383 fix pulse
> multipliers` (2026-08-26) turned `PULSE_BOOST` from the scalar `2.0`
> into a per-risk map with medium at ×3, and neither Aug 26 commit was
> logged. Treat `keno_pick_one.py` as the source of truth.

Rolling Pulse and being paid for it are different events. `pulse_pay`
refuses to rescue a 0× row, so on `high_pick_10_earn` Pulse rolls on
10.0% of rounds and pays on 0.51% — the other 9.49% is a roll the player
never sees. `export_luts.py` now emits **`pulseRolled`** alongside
`pulse` (the boost actually applied) so the client and telemetry can
tell the two apart.

## Buy chips

Both chips are booked math as of 2026-08-28. `solve_buy()` solves them in the
same pass as Earn, with `bought=True` (extras forced open — that is the entire
purchase) and rows denominated in **cost units**, scaled by the cost on export.
Lumen and Pulse then apply at the normal risk rate.

> ⚠️ Until 2026-08-28 these were 80 uncertified LUTs shipping to players:
> `paytables.json` had no `buy10`/`buy100` key, nothing here generated them, and
> the exporter carried them forward with a warning. They boosted Lumen by their
> *cost*, which routed 90–99% of the return through a channel that fires on a
> minority of rounds and left the base table decorative. See the client wiki's
> `wiki/domain/keno-bonuses.md` for the before/after.

### Ceiling: one solve per cost, not one solve scaled twice

The two ladders were briefly a single cost-unit table multiplied by 10 and 100,
which is valid only while every gate is per-cost. **Max payout multiplier is
not** — it is measured against the base bet (see [[domain/stake-rating-limits]]),
so the chips have genuinely different ceilings in cost units and cannot share a
table.

`MAX_PAYOUT_ABS` in `solve_paytables.py` holds the base-bet ceiling per cost,
each ~10% under the tier it answers to, and `cap_for` divides it by the cost:

| cost | ceiling | binding tier | worst shipped |
| --- | --- | --- | --- |
| 1× (Off / Earn) | 100,000× | — (peaks at 4,900×) | 4,900× |
| 10× | 45,000× | 2-Star 50,000× (had reached 49,000×) | 45,000× |
| 100× | 90,000× | 3-Star 100,000× (cannot reach 2-Star) | 90,000× |

Costs `high`'s buy100 top row 1,225× → 225× of cost. The RTP redistributes into
the mid tiers, so hit / win / LDW / push frequencies are unchanged and only
volatility moves (mean SD 5.41 → 5.17 across all 160 modes).

Two traps, both hit while implementing it:

- The cap must lower the `RISK_SHAPES[risk]["top"]` that the `CAP_FRACTION`
  ladder steps down from. Clamping each tier independently flattens the top two
  onto one value, and the monotonicity nudge in `_fill_from` then has to break
  the cap to keep payouts increasing — medium buy100 produced 150.1 against its
  own 150.0 cap that way.
- `check_gates` already had `max_m`, but that is per-cost and cannot see a row
  multiplied by 100 on export. The absolute check is separate.

## Volatility rating: `TOP_OVERRIDE`

`MAX_PAYOUT_ABS` answers a hard gate. `TOP_OVERRIDE` answers a **rating**: the
dashboard prints a categorical volatility label next to the number, and rated
`high_pick_6` Extreme at std 25.73 — barely half the 2-Star stddev ceiling of 50.
See [[domain/stake-rating-limits]].

Only pick 6 was flagged, and the reason is structural rather than a bad ladder. A
top row contributes `p(top) · m²` to variance; `p` falls ~15× per pick while the
ceiling rises, so the product peaks mid-ladder:

| high, Off | top prize | p(top) | std | top row's share of variance |
| --- | --- | --- | --- | --- |
| pick_5 | 867× | 3.8e-4 | 17.59 | 93% |
| **pick_6** | **3,373×** | **5.5e-5** | **25.73** | **94%** |
| pick_7 | 4,900× | 6.4e-6 | 16.58 | 56% |
| pick_8 | 4,700× | 5.9e-7 | 18.31 | 4% |

Pick 6 is the one place where the ceiling is already large *and* still probable
enough to matter; past it the jackpot is too rare to move variance, and the std
comes from mid tiers instead. So capping the ceiling is the entire fix, and it is
close to free: the set of paying tiers does not change, so **hit rate is
untouched** (0.1528 before and after) and the freed RTP redistributes.

`TOP_OVERRIDE` is keyed `(risk, k)` and applied in `cap_for` alongside the
max-payout limit — deliberately not `RISK_SHAPES[risk]["top"]`, which is shared by
every pick and would drag picks 7–10 down from 4,900× with it.

| `("high", 6)` = 2,000× | before | after |
| --- | --- | --- |
| `high_pick_6` std | 25.73 | **16.40** |
| `high_pick_6` top | 3,372.6× | 2,000× |
| `high_pick_6_earn` std | 15.99 | 14.55 |

2,000× was chosen to land pick 6 between pick_7 (16.58) and pick_9 (16.11) — in
line with a ladder the dashboard was already accepting, rather than at a guessed
threshold. It moves exactly 2 of 160 modes; buy10 (14.06) and buy100 (7.80) were
already solving under the new ceiling and did not move at all, since their RTP is
split into the Lumen channel. Off was the outlier precisely because it has no such
channel to absorb the tail.

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
only**. Do not use them for certified payout.

> ⚠️ This page claimed the mock jurisdiction sets
> `disabledBuyFeature: true`. It is `false` in
> `web/src/lib/keno/engine.ts`, so the uncertified buy modes are
> reachable in exactly the configuration we playtest in. The client
> honours the flag correctly once raised (`controls.tsx` `buyLocked`,
> plus two store guards), so any jurisdiction that sets it makes all 80
> buy LUTs unreachable.

Keno is single-shot: `auto_close_disabled=False`. Credit on Play; `EndRound`
only if `round.active`.

See client wiki `wiki/codebase/keno-app.md` / `wiki/codebase/rgs-auth.md`.

## RTP

All **160** modes target **0.9650** (house edge 3.5%), shipping at
0.9630–0.9660 with a 0.30pp cross-mode spread against the 0.50pp gate.

> ⚠️ The rest of this section describes the **0.950** build and its pick_1
> lattices, which the 2026-08-28 re-solve replaced. Kept as the "before" record;
> the current machine-readable state is the client's `src/data/keno-par-sheet.json`
> (`npm run par-sheet`, diff with `scripts/par-diff.mjs`). Cross-mode spread is
> now checked over all 160 modes, not 120 — the buy ladders used to contribute
> one shared set of 40 RTPs because they came from one solve.

All 80 Off/Earn modes previously **targeted** **0.950** (house edge 5%). Off pick_1 is
lattice-locked at 0.950 (classic 0.4/2.6, low 0.5/2.3, medium 0.2/3.2,
high 0.1/3.5). Earn pick_1 uses a different pair so Cross-Mode across 80
modes stays ≤ 0.50pp — classic and low **0.6/1.5** (settled 0.9487),
medium **0.1/2.6** (0.9480), high **0.5/1.4** (0.9515).

> ⚠️ This page said Earn pick_1 classic was `0.2/2.9` settling ~0.9475.
> The Aug 26 re-solve changed it and was not logged. Values above are
> read from `paytables.json` and the shipped LUTs.

Do **not** split miss weight (24+6 remainder). That paid 0.6× and 0.7×
for the same miss on `low_pick_1` and dropped std below the 0.60 floor.

Dashboard gates: hit rate ≥ 2%; Cross-Mode ≤ **0.50pp** over all 80
modes; per-mode RTP ≤ 0.967; Base Mode STD ≥ **0.60** (leave margin —
0.606 displays as 0.60 and fails). local `rgs_verification` only warns
at 5pp RTP spread. Treat warnings as failures.

Re-run against the shipped LUTs on 2026-08-28: all four gates pass. Max
per-mode RTP 0.9515, min hit rate 0.0258 (`high_pick_6`), Cross-Mode
spread 0.350pp (`medium_pick_1_earn` 0.9480 → `high_pick_1_earn`
0.9515), nothing under the 0.62 std the code asserts. The hit-rate gate
has only **0.58pp** of headroom, so any retune that thins the low-hit
rows on `high_pick_6` or `high_pick_9` breaks it first.

See [[domain/stake-engine-publish]] and [[sources/keno-xtreme-analysis]].

## Files

| Path | Owns |
| --- | --- |
| `keno_pick_one.py` | Off + Earn + buy pick_1 lattices; lumen/extra criteria; `lumen_pay` |
| `solve_paytables.py` | `solve_off` / `solve_earn` / `solve_buy`; cap ladder incl. `MAX_PAYOUT_ABS` and `TOP_OVERRIDE`; `check_gates` |
| `paytables.json` | `risks` (Off) + `earn` + `buy10` + `buy100` + `solved` (which sections this solve owns) |
| `run.py` / `export_luts.py` | 160-mode books; Off hypergeometric; Earn/buy lumen×extra weights; `pulseRolled`; writes the client's `src/data/keno-books.json` |
| `utils/rgs_verification.py` | vendored; local gate mirror. `max_win` added to `mode_limits` 2026-08-28 |

`export_luts.py` resolves the client path at run time: monorepo `web/`
first, then a sibling `lumen-keno/` checkout, overridable with
`KENO_WEB_BOOKS`. It no longer `makedirs` the target — a missing
directory means the checkout layout is not what we assumed, and creating
a phantom `web/` silently strands the export.

Publish only `library/publish_files/`.

## Related

- Skill `keno-math`
- [[domain/stake-engine-publish]]
- [[sources/keno-xtreme-analysis]]
