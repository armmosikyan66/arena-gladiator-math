---
type: codebase
tags: [keno, luma-keno, rtp, publish, telemetry]
updated: 2026-09-02
---

# Luma Keno math

Hit-count keno in `math/games/luma-keno/`. `win_type = "other"`. Skill
`keno-math`. Not a slot and not Tower. How Off multipliers are generated:
[[concepts/keno-paytable-generation]].

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
multiplies by `LUMEN_BOOST` — **×2 on every risk**. Buy chips use
`BUY_LUMEN_BOOST` instead (**10× / 100×**). Lumen does **not** rescue a 0× row.

> ⚠️ This page said high was ×5 until 2026-08-28. At ×5 it carried 67–74% of the
> return on picks 5–10 through a channel paying on ~2.6% of rounds, leaving the
> base table at ~14%; the re-solve dropped it to ×2.

Earn extras: 0 or 2 from the remaining 30 (`lumen` / `nearMiss` / luck).
Extra hits pay the Earn table, then Lumen multiplies that base.

Earn Pulse: a **charge on an extra light**, so it rolls on **10% of the
books whose extras open** and never when they stay closed. Boost ×2 on
classic/low/high and **×3 on medium**, applied after Lumen and only on a
paying table. Buy chips always open extras, so their roll rate stays a flat
10% of rounds.

> ⚠️ This page said "×2" uniformly until 2026-08-28. `f506383 fix pulse
> multipliers` (2026-08-26) turned `PULSE_BOOST` from the scalar `2.0`
> into a per-risk map with medium at ×3, and neither Aug 26 commit was
> logged. Treat `keno_pick_one.py` as the source of truth.

Rolling Pulse and being paid for it are different events. `pulse_pay`
refuses to rescue a 0× row, so a rolled Pulse on a dead table is a roll the
player never cashes. `export_luts.py` emits **`pulseRolled`** alongside
`pulse` (the boost actually applied) so the client and telemetry can tell the
two apart.

> ⚠️ Until 2026-08-30 Pulse was an **independent** 10% round roll — it split
> closed-extras books too, which the client never had a face for (the rings
> mount on an extra light) and the `keno-math` skill had always forbidden.
> Gating it to extra-open books kept every (hits, lumen, extras, extraHits)
> marginal identical and changed only the Earn coefficient, so the Earn
> ladders were re-solved to the same 0.9650 target. Buy math is bit-identical
> (their extras never close); Off never had Pulse. One engine trap surfaced:
> `run_multi_process_sims` floors `sims_per_thread = int(n / repeats)`, so a
> 99-book mode against `batching_size = 50` split into 2 repeats of 49 and
> silently dropped a book — every Earn count used to be even (all books were
> pulse-split), so odd counts never occurred before. `run.py` now uses a batch
> of 1000 (any batch ≥ the largest count forces one lossless repeat).

## Buy chips

Both chips are booked math as of 2026-08-28. `solve_buy()` solves them in the
same pass as Earn, with `bought=True` (extras forced open) and rows
denominated in **cost units**, scaled by the cost on export.

**Buy 10× and Buy 100× (picks 2–10)** both place the Lumen mark on one of
the player's numbers and **force that pick into the main ten**
(`lumen_placed_on_pick`, `kenoStart.lumenPlaced`). Catch rate is **1**.
P(h=0)=0. Remaining hits: Hypergeometric on k−1 picks vs 9 draws from 39.
pick_1 cannot carry the placement (forcing the only pick in collapses
variance below Base Mode STD) but still uses the chip boost at the Earn
catch rate. Dashboard Base Mode STD is cost=1 only — `check_gates` does
not apply `STD_MIN` to buy chips.

Lumen on a paying catch is **`BUY_LUMEN_BOOST`**: 10× on buy10, 100× on
buy100 — not the Earn ×2. Pulse stays at the risk rate. The boost is priced
into the coefficients so advertised rows shrink (every paying book now
carries ×10/×100). Do not stack 10×/100× on the old Earn-rate tables. The
buy ladder uses a **0.1×-of-stake grid** in cost units (`0.01` / `0.001`)
because a 0.1-of-cost cell ×100 Lumen is 1,000× the base bet and overshoots
target. `lumen_pay` rounds to 0.1× the base bet
(`round(amount * cost, 1) / cost`), not 0.1 of cost units.

### ETL sum: every paying buy row catches Lumen

Dashboard **Expected Tail Liability (Sum)** is etl40 + etl10k. A win that is
both ≥40× cost and ≥10,000× the base bet is counted twice. Guaranteed catch
puts the chip boost on every paying row, not only the full card.

`settled_stats(..., cost=)` cuts etl10k at `10000/cost`, and `check_gates`
fails `etl_sum > 1.45`. When it fires, `solve_table` shrinks the advertised
top — first to just under the 10k/Lumen line — and refills. Do not clamp.

Shipped 2026-08-31 `high_pick_4_buy100` (base-bet row): `[0, 0, 0, 0.9,
40.2]`. Lumen-only top 4,020×; Pulse-on-top 8,040×. etl_sum **0.798**. RTP
0.9652. `high_pick_4_buy10`: same advertised row; Lumen 402×; Pulse 804×.

> ⚠️ `_fill_from`'s water-fill used to `hi *= 2` until tail RTP reached the
> leftover budget. After an etl shrink the tail can be capped below that
> budget, so the loop never returned. It now fills to cap and leaves the
> residual for the grid / RTP gate.

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

See [[domain/stake-engine-publish]], [[sources/keno-xtreme-analysis]],
[[sources/keno-xtreme-easy-hud]], [[sources/keno-xtreme-classic-hud]],
[[sources/keno-xtreme-medium-hud]], and [[sources/keno-xtreme-hard-hud]].

## Easy HUD vs Off `low`

Keno Xtreme **Easy** (competitor) pick × hit multipliers, transcribed in
[[sources/keno-xtreme-easy-hud]]. Skill `keno-math` maps that to luma-keno
**Off `low`**: copy shape + maxes, snap illegal cells to 0.1×, retarget
body RTP to the 0.964 fleet. Easy pick_2 HUD `1.90/4.50` is 0.990 RTP;
the published snap is `1.8/4.7`. Easy tops are **2 / 4.5 / 10.4 / 22.5 / 36 /
40 / 60 / 70 / 85 / 100** — do not replace 70/85/100 with 400× on Off.

**Shipped 2026-09-01** (competitor HUD, provenance):

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.65 | 2.00 | | | | | | | | | |
| **2** | 0.00 | 1.90 | 4.50 | | | | | | | | |
| **3** | 0.00 | 1.00 | 3.10 | 10.40 | | | | | | | |
| **4** | 0.00 | 0.80 | 1.80 | 5.00 | 22.50 | | | | | | |
| **5** | 0.00 | 0.25 | 1.40 | 4.10 | 16.50 | 36.00 | | | | | |
| **6** | 0.00 | 0.00 | 1.00 | 3.68 | 7.00 | 16.50 | 40.00 | | | | |
| **7** | 0.00 | 0.00 | 0.47 | 3.00 | 4.50 | 14.00 | 31.00 | 60.00 | | | |
| **8** | 0.00 | 0.00 | 0.00 | 2.20 | 4.00 | 13.00 | 22.00 | 55.00 | 70.00 | | |
| **9** | 0.00 | 0.00 | 0.00 | 1.50 | 3.00 | 8.00 | 15.00 | 44.00 | 60.00 | 85.00 | |
| **10** | 0.00 | 0.00 | 0.00 | 1.40 | 2.25 | 4.50 | 8.00 | 17.00 | 50.00 | 80.00 | 100.0 |

Off `low` **is** that copy as of 2026-09-01 — `easy_off_low.py` is the
designed chart (validated at import: 0.1× lattice, HUD shape, strictly
increasing ladder and per-pick maxes, exact RTP window 0.9630–0.9655) and
`solve_paytables.py` uses it instead of solving. Picks 2 / 7 / 10 are the
snaps already published in the skill; 3 / 4 / 5 / 6 / 8 / 9 were derived
under the same rules (keep the max, fewest moved cells, least drift).
pick_1 stays on the `PICK_ONE_MISS` lattice (miss 0.5).

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | max | RTP |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.50 | 2.30 | | | | | | | | | | 2.3 | 0.9650 |
| **2** | 0.00 | 1.80 | 4.70 | | | | | | | | | 4.7 | 0.9635 |
| **3** | 0.00 | 0.60 | 4.20 | 10.40 | | | | | | | | 10.4 | 0.9644 |
| **4** | 0.00 | 0.80 | 1.70 | 4.90 | 22.50 | | | | | | | 22.5 | 0.9642 |
| **5** | 0.00 | 0.20 | 1.40 | 4.10 | 16.10 | 36.00 | | | | | | 36.0 | 0.9652 |
| **6** | 0.00 | 0.00 | 1.00 | 3.60 | 6.40 | 16.50 | 40.00 | | | | | 40.0 | 0.9652 |
| **7** | 0.00 | 0.00 | 0.40 | 3.00 | 4.40 | 14.40 | 31.00 | 60.00 | | | | 60.0 | 0.9635 |
| **8** | 0.00 | 0.00 | 0.00 | 2.10 | 4.00 | 12.80 | 22.00 | 55.00 | 70.00 | | | 70.0 | 0.9653 |
| **9** | 0.00 | 0.00 | 0.00 | 1.50 | 3.00 | 7.50 | 15.00 | 44.00 | 60.00 | 85.00 | | 85.0 | 0.9641 |
| **10** | 0.00 | 0.00 | 0.00 | 1.40 | 2.10 | 4.40 | 8.00 | 17.00 | 50.00 | 80.00 | 100.0 | 100 | 0.9641 |

Illegal-cell snaps and the trims that reach the window: `0.25→0.2`,
`3.68→3.6` (+`7.0→6.4`), `0.47→0.4` (`4.5→4.4`, `14→14.4`), `2.25→2.1`
(`4.5→4.4`). Pick 3 trims `1.0→0.6` and raises `3.1→4.2` (its HUD body
underpays low hits, so the budget moves up-ladder); pick 4 trims `1.8→1.7`,
`5.0→4.9`; pick 8 trims `2.2→2.1`, `13→12.8`; pick 9 trims `8→7.5`.
Maxes move only on pick 2 (`4.5→4.7`). Earn `low`
and the buy chips are untouched — they keep their own ladders (Earn low
pick_8–10 advertise ~100× so Lumen×2 × Pulse×2 settles 400×).

## Classic HUD vs Off `classic`

Keno Xtreme **Classic** (docx: Normal) is [[sources/keno-xtreme-classic-hud]]
/ [[domain/keno-xtreme-classic]]. Off `classic` copies **zeros + maxes**, then
fills the body with a max-anchored geometric ladder onto 0.9650
(`easy_off_classic.py`). HUD is **42.2–90.6% RTP** on picks 2–10 so leftover
must rise. Tops: **2.6 / 5.4 / 17.5 / 30 / 75 / 200 / 600 / 750 / 900 / 1000**
(pick_1 advertised 0.4/2.6 plus 1-in-5 miss bonus at 0.5×, LUT RTP 0.9650;
pick 2 HUD 5.00 has no in-window lattice point).

Shipped Off `classic` (2026-09-01 geometric):

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.40 | 2.60 | | | | | | | | | |
| **2** | 0.00 | 1.70 | 5.40 | | | | | | | | |
| **3** | 0.00 | 0.00 | 3.50 | 40.00 | | | | | | |
| **4** | 0.00 | 0.00 | 1.30 | 11.60 | 100.0 | | | | | |
| **5** | 0.00 | 0.00 | 0.50 | 4.50 | 37.00 | 300.0 | | | | |
| **6** | 0.00 | 0.00 | 0.00 | 2.90 | 16.40 | 91.00 | 500.0 | | | |
| **7** | 0.00 | 0.00 | 0.00 | 1.90 | 8.20 | 34.40 | 144.2 | 600.0 | | |
| **8** | 0.00 | 0.00 | 0.00 | 1.30 | 4.90 | 17.10 | 60.10 | 212.0 | 750.0 | |
| **9** | 0.00 | 0.00 | 0.00 | 1.00 | 3.20 | 9.50 | 30.50 | 92.70 | 290.1 | 900.0 |
| **10** | 0.00 | 0.00 | 0.00 | 0.80 | 2.20 | 6.30 | 16.70 | 47.70 | 129.3 | 360.7 | 1000 |

Earn `classic` and the buy chips keep their own ladders.

## Medium HUD vs Off `medium`

Keno Xtreme **Medium** (docx: Crazy) is [[sources/keno-xtreme-medium-hud]]
/ [[domain/keno-xtreme-medium]]. How the shipped multipliers are generated:
[[concepts/keno-paytable-generation]] Algorithm A (same geometric ladder
as classic). Jackpot-shaped. Competitor pick 1 is even money `0.00/4.00`;
luma-keno pick_1 stays the miss-bonus lattice `[0.2, 3.2]`. Pick 3 HUD
**75×** is **115% RTP** and fails ETL40 — Off ships **60.3×** (65.8× is
the absolute 0.80 ceiling). Pick 2 HUD **9.00** has no in-window pair
(snap **9.4**). Pick 4 HUD **175.0** rejects (snap **174.9**).

Competitor HUD:

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.00 | 4.00 | | | | | | | | | |
| **2** | 0.00 | 0.95 | 9.00 | | | | | | | | |
| **3** | 0.00 | 0.00 | 1.75 | 75.00 | | | | | | |
| **4** | 0.00 | 0.00 | 0.95 | 7.00 | 175.0 | | | | | |
| **5** | 0.00 | 0.00 | 1.20 | 3.00 | 9.00 | 450.0 | | | | |
| **6** | 0.00 | 0.00 | 0.00 | 1.50 | 5.00 | 50.00 | 650.0 | | | |
| **7** | 0.00 | 0.00 | 0.00 | 0.95 | 3.00 | 7.50 | 90.00 | 750.0 | | |
| **8** | 0.00 | 0.00 | 0.00 | 0.95 | 2.00 | 5.00 | 15.00 | 150.0 | 2500 | |
| **9** | 0.00 | 0.00 | 0.00 | 0.95 | 1.10 | 2.50 | 5.00 | 40.00 | 350.0 | 4000 |
| **10** | 0.00 | 0.00 | 0.00 | 0.50 | 0.95 | 1.50 | 3.00 | 9.00 | 40.00 | 400.0 | 5000 |

**Shipped 2026-09-02** (geometric, HUD zeros, max-anchored onto 0.9650):

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.20 | 3.20 | | | | | | | | | |
| **2** | 0.00 | 1.10 | 9.40 | | | | | | | | |
| **3** | 0.00 | 0.00 | 1.70 | 60.30 | | | | | | |
| **4** | 0.00 | 0.00 | 0.70 | 10.50 | 174.9 | | | | | |
| **5** | 0.00 | 0.00 | 0.30 | 3.90 | 41.80 | 450.0 | | | | |
| **6** | 0.00 | 0.00 | 0.00 | 2.60 | 16.60 | 103.8 | 650.0 | | | |
| **7** | 0.00 | 0.00 | 0.00 | 1.80 | 8.10 | 36.80 | 165.3 | 750.0 | | |
| **8** | 0.00 | 0.00 | 0.00 | 0.90 | 4.40 | 21.50 | 104.5 | 512.4 | 2500 | |
| **9** | 0.00 | 0.00 | 0.00 | 0.70 | 2.60 | 11.60 | 51.00 | 216.3 | 932.9 | 4000 |
| **10** | 0.00 | 0.00 | 0.00 | 0.50 | 1.90 | 7.10 | 25.90 | 97.30 | 362.1 | 1343.3 | 5000 |

Earn `medium` and the buy chips keep their own ladders.

## Hard HUD vs Off `high`

Keno Xtreme **Hard** (docx: Degen) is [[sources/keno-xtreme-hard-hud]]
/ [[domain/keno-xtreme-hard]]. How the shipped multipliers are generated:
[[concepts/keno-paytable-generation]] Algorithm A (same geometric ladder
as classic/medium). Jackpot-or-bust. Competitor pick 1 is even money
`0.00/4.00`; luma-keno pick_1 stays the miss-bonus lattice `[0.1, 3.5]`.
Picks **2–6 HUD tops are player-favor** (pick 3 at 500× is ~614% RTP) —
Off ships the highest in-window / gate-legal max instead. Picks 6–10 keep
the HUD jackpots; 10/10 stays **50,000×**.

Competitor HUD:

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.00 | 4.00 | | | | | | | | | |
| **2** | 0.00 | 0.00 | 20.00 | | | | | | | | |
| **3** | 0.00 | 0.00 | 0.50 | 500 | | | | | | |
| **4** | 0.00 | 0.00 | 0.00 | 1.50 | 1000 | | | | | |
| **5** | 0.00 | 0.00 | 0.00 | 0.50 | 25.00 | 2500 | | | | |
| **6** | 0.00 | 0.00 | 0.00 | 0.25 | 1.50 | 350.0 | 6000 | | | |
| **7** | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 | 3.00 | 950.0 | 12500 | | |
| **8** | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 | 1.50 | 40.00 | 1500 | 25000 | |
| **9** | 0.00 | 0.00 | 0.00 | 0.10 | 0.30 | 0.50 | 5.00 | 40.00 | 3500 | 40000 |
| **10** | 0.00 | 0.00 | 0.00 | 0.10 | 0.30 | 0.50 | 1.50 | 3.00 | 90.00 | 4500 | 50000 |

**Shipped 2026-09-02** (geometric, HUD zeros, max-anchored onto 0.9650):

| k \ h | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | 0.10 | 3.50 | | | | | | | | | |
| **2** | 0.00 | 0.00 | 16.70 | | | | | | | | |
| **3** | 0.00 | 0.00 | 0.70 | 71.60 | | | | | | |
| **4** | 0.00 | 0.00 | 0.00 | 2.20 | 382.4 | | | | | |
| **5** | 0.00 | 0.00 | 0.00 | 0.10 | 8.00 | 2297.8 | | | | |
| **6** | 0.00 | 0.00 | 0.00 | 0.30 | 7.40 | 214.5 | 6000 | | | |
| **7** | 0.00 | 0.00 | 0.00 | 0.30 | 4.10 | 59.80 | 865.6 | 12500 | | |
| **8** | 0.00 | 0.00 | 0.00 | 0.20 | 2.50 | 23.70 | 242.6 | 2464.1 | 25000 | |
| **9** | 0.00 | 0.00 | 0.00 | 0.20 | 1.60 | 11.70 | 90.80 | 690.2 | 5252.2 | 40000 |
| **10** | 0.00 | 0.00 | 0.00 | 0.20 | 1.20 | 6.70 | 40.20 | 240.3 | 1424.6 | 8436.9 | 50000 |

Earn `high` and the buy chips keep their own ladders.

## Files

| Path | Owns |
| --- | --- |
| `keno_pick_one.py` | Off + Earn + buy pick_1 lattices; lumen/extra criteria; `lumen_pay` |
| `easy_off_low.py` | Designed Off `low` chart (Keno Xtreme Easy leftover-share, picks 2–10); validates at import |
| `easy_off_classic.py` / `easy_off_medium.py` / `easy_off_high.py` | Off geometric HUD copies (classic / medium / high); `generate_classic_row` is the shared solver |
| `solve_paytables.py` | `solve_off` / `solve_earn` / `solve_buy`; cap ladder incl. `MAX_PAYOUT_ABS` and `TOP_OVERRIDE`; `JACKPOT_TOP` pins picks 4–10 (Off/Earn 4–8 via `jackpot_applies`); Off `low` bypasses this via `easy_off_low.py`; `check_gates` |
| `paytables.json` | `risks` (Off) + `earn` + `buy10` + `buy100` + `solved` (which sections this solve owns) |
| `run.py` / `export_luts.py` | 160-mode books; Off hypergeometric; Earn/buy lumen×extra weights; extra-gated `pulseRolled`; writes the client's `src/data/keno-books.json` |
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
- [[domain/keno-xtreme-easy]] — Easy pick 1–10 hit multipliers.
- [[domain/keno-xtreme-classic]] — Classic pick 1–10 hit multipliers.
- [[domain/keno-xtreme-medium]] — Medium pick 1–10 hit multipliers.
- [[domain/keno-xtreme-hard]] — Hard / Degen pick 1–10 hit multipliers.
- [[sources/keno-xtreme-analysis]]
- [[sources/keno-xtreme-easy-hud]] — Keno Xtreme Easy pick×hit matrix (screenshots 2026-08-31).
- [[sources/keno-xtreme-classic-hud]] — Keno Xtreme Classic pick×hit matrix (screenshots 2026-09-01).
- [[sources/keno-xtreme-medium-hud]] — Keno Xtreme Medium pick×hit matrix (screenshots 2026-09-01).
- [[sources/keno-xtreme-hard-hud]] — Keno Xtreme Hard pick×hit matrix (screenshots 2026-09-01).
