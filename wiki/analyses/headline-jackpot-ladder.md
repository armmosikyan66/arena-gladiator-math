---
type: analysis
tags: [keno, luma-keno, paytable, jackpot, competitive, volatility, rating-limits, psychology]
updated: 2026-08-31
---

# Headline jackpot ladder

Queried 2026-08-31. The question: _our top multipliers do not read as
competitive against Keno Xtreme. What does Stake actually allow, and what is the
largest headline we can carry without lying about it?_

The answer: **five-figure headlines are nearly free — but only at picks 9 and
10.** Everywhere else the top row is load-bearing for volatility. A second pass
the same day pinned picks 4–8 to declared *round* ceilings the water-fill had
abandoned (low pick 8 was advertising 3.6× against a 400× cap). Those are
`RISK_SHAPES`-scale numbers, not 50,000×; the original "not free mid-ladder"
claim still holds for Xtreme-scale tops.

Shipped the same day. Mechanism: `JACKPOT_TOP` in `solve_paytables.py`
([[codebase/luma-keno]]). Limits: [[domain/stake-rating-limits]]. Competitor
claims: [[sources/keno-xtreme-analysis]].

---

## Where we stood

| | headline max win |
| --- | --- |
| Stake Originals Keno | 1,000× |
| Keno Xtreme (third-party listings) | 50,000×–100,000× ⚠️ unverified |
| **luma-keno, before** | **4,900×** (`high_pick_9`) |
| Stake dashboard, 3-Star | 100,000× |

4,900× was not a decision. It is `RISK_SHAPES["high"]["top"]`, a shaping
parameter shared by every pick, and no mode had ever been solved against the
actual ceiling. Against a competitor advertising five or six figures, the number
on our rules screen was a rounding error on what we were allowed to print.

> ⚠️ The Xtreme figure is a third-party listing, not something we verified in
> their math (from [[sources/keno-xtreme-analysis]]). It sets the perception we
> compete against, not a number we owe parity with.

## Why the ceiling was reachable at picks 9–10 and nowhere else

A top row contributes `p(top) · m` to RTP and `p(top) · m²` to variance. Both
scale with `p`, and `p` collapses roughly 15× per pick while the ceiling stays
flat. So the same headline costs wildly different amounts depending on where it
sits.

At the full card the probability is small enough that the row is almost free:

| mode | top prize | odds of the top row | cost of the whole top row in RTP |
| --- | --- | --- | --- |
| `high_pick_10` | 100,000× | 1 in 847,660,528 | 0.012pp |
| `high_pick_9` | 25,000× | 1 in 27,343,888 | 0.091pp |
| `high_pick_6` | 2,000× | 1 in ~18,000 | 11pp |

Pick 6 is the counter-example and it is already documented: it was rated
**Extreme** at std 25.73 on a 3,373× top row, and capping it to 2,000× was the
entire fix ([[codebase/luma-keno]], `TOP_OVERRIDE`). Mid-ladder the top row is
**94%** of variance. At picks 9–10, even carrying a five-figure jackpot, it is
**7–19%** — the row is too rare to dominate the second moment no matter how large
`m` gets, because `p` fell faster than `m` rose.

This is the whole result for *five-figure* headlines: **the rows that make a
headline impressive are the ones that cost nothing, and the rows that cost
something make no headline.** Raising picks 5–8 to 50,000× would still buy a
smaller number for a real price in mid-tier pay. Restoring the *declared*
400–5,000× ceilings is a different move — see [Picks 4–8](#picks-48-restoring-declared-ceilings).

## The ladder

`JACKPOT_TOP`, applied only at `h == k`. Picks 1–3 unpinned (lattice / Earn RTP).
Picks 4–8 Off/Earn only (`jackpot_applies`); picks 9–10 pin every kind.

| risk | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low | 50× | 150× | 400× | 1,000× | 2,000× | 4,000× | 20,000× |
| classic | 100× | 300× | 800× | 2,000× | 3,500× | 8,000× | 40,000× |
| medium | 200× | 600× | 1,500× | 3,000× | 5,000× | 15,000× | 60,000× |
| high | 350× | 900× | 2,000× | 5,000× | 6,000× | 25,000× | **100,000×** |

Growth per pick, which is the property to check when editing this:

| risk | 4→5 | 5→6 | 6→7 | 7→8 | 8→9 | 9→10 |
| --- | --- | --- | --- | --- | --- | --- |
| low | 3.00× | 2.67× | 2.50× | 2.00× | 2.00× | 5.00× |
| classic | 3.00× | 2.67× | 2.50× | 1.75× | 2.29× | 5.00× |
| medium | 3.00× | 2.50× | 2.00× | 1.67× | 3.00× | 4.00× |
| high | 2.57× | 2.22× | 2.50× | 1.20× | 4.17× | 4.00× |

Rarity grows 6.0× / 7.0× / 8.5× / 11.0× / 16.0× / 31.0× across the same steps, so
every step underpays the odds ratio — unavoidable, since paying the full-card
ratio at pick 10 would mean an 847,660,528× prize. What matters is that the
ladder never *reverses* or flattens against it.

Three properties were deliberate:

- **100,000× is the 3-Star ceiling exactly** — the deliberate exception to this
  repo's design-below-the-published-maximum rule, taken because the headline is
  the entire purpose of the row. `check_gates` uses `>`, so exactly 100,000×
  passes, and the advertised row is grid-floored before the settle multiply so
  Earn cannot drift over. It also lands level with the top of the 50,000×–100,000×
  range claimed for Keno Xtreme, which is the comparison that started this.
- **Risk ordering is preserved and the gap widens with risk.** `high` pays 5×
  what `low` pays at pick 10, so the risk selector still means something at the
  top of the ladder, which is where players look when deciding.
- **Round numbers.** 100,000× reads as a decision; 89,412× reads as an artifact.
  The previous ladder was full of artifacts (4,699.8×, 3,372.6×, 1,299.8×) because
  the water-fill chose them, and an artifact at the headline undercuts the claim.

> ⚠️ **Sitting on the limit is a real exposure, and it is the one thing here worth
> re-deciding.** The dashboard was observed reporting `490,000 / 100,000` for
> 3-Star, so the number itself is right, but a `>=` comparison on their side or any
> rounding difference in how `max_win` is computed would reject the publish. The
> fallback is a one-line change back to 90,000× and nothing else in the ladder
> depends on it. This mode also **requires** a 3-Star rating — 2-Star's ceiling is
> 50,000× and cannot carry it.

### Psychology: why the top row and not the reachable tiers

The headline is doing availability work, not expected-value work. It is read
once, before the first bet, when the player is comparing us to another tile in a
lobby — and at that moment 100,000× and 4,900× are not two numbers on the same
scale, they are two different categories of game. What follows the decision is
governed by hit frequency and the mid tiers, and **those are byte-identical
after this change** (see below). So the change buys the comparison and touches
nothing about the actual session.

The honest framing matters too, and it is already enforced: `hitFreq`,
`pTop`, and `oneIn` all ship in the PAR sheet, the rules screen states max win
against the armed mode, and the copy gate fails on a claim the tables do not
support. A 1-in-847,660,528 jackpot is fine to advertise loudly **as long as the
odds travel with it**, which is exactly the standard the client's copy eval
already holds us to.

> ⚠️ Do not read this as license to raise the headline further by starving mid
> tiers. The property that made this free — negligible `p(top)` — does not exist
> anywhere else on the ladder, and the next 10,000× would have to be paid for by
> someone.

## What it cost

28 of 160 modes changed. Nothing that describes the felt experience moved:

| | before | after |
| --- | --- | --- |
| RTP, all 160 modes | 0.9630–0.9664 | **0.9630–0.9664** (spread 0.0034, limit 0.005) |
| largest single RTP move | — | **0.09pp** (`high_pick_9_earn`, 0.9654 → 0.9645) |
| `hitFreq` / `winFreq` / `ldwFreq` / `pushFreq` / `zeroFreq` | | **0 of 160 modes changed** |
| `pTop` / `oneIn` | | **0 of 160 modes changed** |
| mean std | 4.74 | 4.94 |
| worst std | 18.31 (`high_pick_8`) | **18.74** (`high_pick_10_earn`) |
| headline max win | 4,900× | **100,000×** |

The set of paying tiers is identical, so hit rate cannot move; only the second
moment does, and only where a jackpot was pinned.

Gate margins at the new ceiling, from the solver's own `check_gates` (0 failures
across 160 modes):

| gate | worst mode | value | limit |
| --- | --- | --- | --- |
| max payout | `high_pick_10` | **100,000×** | 100,000× (3-Star) — *on* the limit |
| std | `high_pick_10_earn` | 18.74 | 55 |
| CVaR | `high_pick_4` | 344.5 | 700 |
| etl_sum | `high_pick_4_buy10` | 0.798 | 1.45 |

Every hard gate has wide margin, and the CVaR / ETL worst cases are not even
jackpot modes. The one number that moved into unknown territory is volatility.

### ⚠️ `high_pick_10_earn` is now the most volatile mode in the game

At 90,000× it was 17.66. At 100,000× it is **18.74**, which passes the hard gate
(55) by a mile but is the first time any mode has gone above `high_pick_8`'s
18.31 — and 18.31 is the top of the range the dashboard was *observed* not to
flag. The Extreme boundary lies somewhere in **(18.3, 25.73]**; we do not know
where ([[domain/stake-rating-limits]]).

So this mode may come back labelled **EXTREME**. That is a rating, not a
rejection, but the precedent in this repo is to treat the label as something to
fix: `TOP_OVERRIDE` exists because `high_pick_6` was flagged at 25.73
([[codebase/luma-keno]]).

**Resolved 2026-09-03 — superseded by the Off/Earn parity pass.** Earn high
pick 10 no longer carries a 100,000× headline: it advertises 12,500 (settles
50,000 = Off pick 10), pick 9 advertises 10,000 (settles 40,000 = Off pick 9).
`high_pick_10_earn` std fell 26.63 → 12.96, back under `high_pick_8`'s
observed-safe band, and the sitting-on-the-ceiling publish exposure (`>=` read
on the dashboard side) is gone. Both new rows are lock-clean with the final
catch at exactly 15×. The historical options below are kept for context.

Two ways out if it is flagged, in order of preference:

1. **Hold Earn at 90,000× and let Off carry 100,000× alone** — `jackpot_advertised`
   already takes `earn`, so this is a per-kind value rather than a new mechanism.
   Cost: with the bonus armed the rules screen would show a *lower* max win than
   with it off, which is true but reads badly.
2. **Drop both back to 90,000×** — one line, returns the worst mode to
   `high_pick_8` at 18.31, and keeps Off and Earn consistent.

Neither is needed unless the dashboard actually prints the label. Recorded here so
the next person does not rediscover it from a publish failure.

## Side effect: two collapsed ceilings got fixed

Pinning the top row also repaired advertised ceilings that the water-fill had
been quietly abandoning.

**Earn.** Lumen and Pulse add probability mass to the paying rows, so the
water-fill spread the Earn budget wider and left the top row starved.
`low_pick_10_earn` advertised **9.6×** — a "max win" below the mid tiers of its
own table, on the mode a player reaches by earning the bonus. Now 20,000×, the
same as its Off counterpart.

**Buy chips.** Max payout is measured against the base bet, so cost divides the
usable ceiling ([[domain/stake-rating-limits]]). `high` was already solving into
that ceiling; the other three risks were not:

| | buy10 (cost 10) | buy100 (cost 100) |
| --- | --- | --- |
| `low_pick_9`, before | 20.4× | 20.4× |
| `low_pick_9`, after | **4,000×** | **900×** |
| `high_pick_10`, 2026-09-03 | **10,000×** | **1,000×** |
| ceiling in cost units | 10,000× (= 100,000× base bet) | 1,000× (= 100,000× base bet) |

All eight pick-9/pick-10 buy chips now sit at the ceiling their cost allows.
`low_pick_9_buy10` was advertising 20.4× where 4,500× was permitted.
**2026-09-03 headline parity:** `high_pick_10` buy10/buy100 raised to 100,000×
the base bet (JSON 5,000 / 500), matching Off/Earn's 3-Star ceiling exactly.

## Picks 4–8: restoring declared ceilings

The 9–10 pass left every other top as a water-fill leftover. The user asked to
update **all** the multipliers, not just the lobby headline. Worst artifact:
`low_pick_8` advertised **3.6×** against a 400× `RISK_SHAPES` cap — a "max win"
below a typical consolation. High 7/8 were still printing 4,900× / 4,699.8×,
the shared shape top, not a decision.

A probe (picks 2–8, Off+Earn, std ≤ 18.3) showed:

- **Picks 2–3 cannot pin.** Earn RTP breaks; those tops are load-bearing.
- **Picks 4–8 have headroom** on low / classic / medium. High is already near
  the observed-safe std. `high_pick_6` stays 2,000× (`TOP_OVERRIDE`) — Extreme
  at 3,373× / std 25.73.
- **High pick 8** max pin at sd 18.3 is ~6,122×. It was already 18.31, the
  highest *unflagged* value — do not push.

So 4–8 is not another Xtreme-scale raise. It pins round, risk-ordered numbers
under the std we have actually seen pass. Some Earn tops **fell** so Off and
Earn advertise the same settled jackpot (`high_pick_4_earn` 442× → 350×,
`medium_pick_5_earn` 835× → 600×). Medium 8 Earn prints 4,999.8 —
`advertised_cap` grid-floors before the settle multiply.

### ⚠️ The first version of this pass shipped plateaus

The values above are the corrected ladder. The first attempt reused
`RISK_SHAPES[risk]["top"]` as the pin for several consecutive picks and produced
flat runs: **low 400× at picks 6, 7 and 8**; classic 800× at the same three;
medium 2,500× at 7 and 8; high 5,000× at 7 and 8.

That is a straightforward design error, not a tuning preference. The full card
gets monotonically rarer in `k`:

| pick | odds of the full card | vs previous pick |
| --- | --- | --- |
| 4 | 1 in 435 | — |
| 5 | 1 in 2,611 | 6.0× |
| 6 | 1 in 18,278 | 7.0× |
| 7 | 1 in 155,363 | 8.5× |
| 8 | 1 in 1,708,993 | 11.0× |
| 9 | 1 in 27,343,888 | 16.0× |
| 10 | 1 in 847,660,528 | 31.0× |

A flat run means an 8-of-8 at 1 in 1,708,993 paid exactly what a 6-of-6 at 1 in
18,278 paid — **94× rarer for the same prize** — and a player reading the
paytable would correctly conclude that adding picks 7 and 8 bought them nothing
at the top. It also left most of the envelope unused: `low_pick_8` was pinned at
400× where 7,218× was available.

The mistake was pinning to a *cap* rather than designing a curve. `cap_for`
returns the pin directly at `h == k`, so `RISK_SHAPES` was never constraining
these values — 400× was just the number sitting nearby in the source.

**Rule now enforced in code.** `_assert_jackpot_ladder_distributed()` runs at
import and raises on either a non-increasing step in `k` or a risk inversion at
any pick, naming the two offending entries. It is 25 lines and it makes the
property that was violated impossible to reintroduce silently.

### The envelope, and why the ladder bends

Binary search per mode against Off + Earn at std ≤ 18.3:

| max pin | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- |
| low | 324 | 935 | 2,471 | 6,105 | 7,218 |
| classic | 382 | 934 | 2,464 | 5,924 | 14,703 |
| medium | 382 | 912 | 2,361 | 6,689 | 17,974 |
| high | 366 | 907 | 2,290 | 5,607 | **6,122** |

Two features of this envelope determine the shape, and both are worth
understanding before touching the numbers:

**It is nearly risk-independent at picks 4–6** — about 370 / 920 / 2,400 for every
risk. The std cap binds on the top row itself, and `p(h == k)` is the same
hypergeometric regardless of risk, so all four converge. The consequence: the risk
dial *cannot* be expressed by pushing each risk to its own ceiling. `low` sits far
under its own limit on purpose, so that low < classic < medium < high keeps
meaning something.

**It stops growing for `high` at pick 8** — 5,607 → 6,122 is only 1.09×, while
low/classic/medium keep climbing to 7,218–17,974. Since the ladder must also be
risk-ordered, `high` becomes the binding constraint for *every* risk at pick 8.
That compresses the risk spread from 7× at pick 4 (50 → 350) to 3× at pick 8
(2,000 → 6,000). Variance is `p · m²`; `p` falls ~11× from pick 7 to pick 8 while
`high`'s mid rows already spend more of the budget, so this is the envelope
talking, not a preference.

The design rule that resolves both: **take the largest round value under the
envelope that keeps the top strictly increasing in `k` and ordered across risk.**
The one soft spot it leaves is high 7→8 at 1.20×. Smoothing that to ~1.5× means
cutting `high_pick_7` from 5,000× to 4,000× — throwing away a real advertised
maximum to buy a prettier ratio — so the shallow step is kept and recorded here
instead.

### Buy chips stay off this pin

A first solve that reused cost-1 pins as cost-units failed 6 buy10 modes: buy10
high pick 4's top is 1-in-435, and 350× of *cost* ate ~80pp of RTP.
`jackpot_applies(k, cost)` now pins 4–8 only when `cost == 1`. Picks 9–10 still
pin every kind so a chip advertises `MAX_PAYOUT_ABS / cost` (4,500× buy10,
900× buy100).

### What the 4–8 pass cost

41 of 160 modes moved across both passes (Off + Earn, picks 4–8). Buy chips
unchanged. The monotonicity correction was the last 14 of those — all at picks 7
and 8, and it moved **no** frequency in any mode.

| | before (post-100k) | after |
| --- | --- | --- |
| RTP, all 160 | 0.9630–0.9664 | **0.9630–0.9664** (spread 0.0034 / 0.005) |
| `hitFreq` / `zeroFreq` / `pTop` / `oneIn` | | **0 of 160 changed** |
| mean win / LDW / push | 0.2770 / 0.2162 / 0.0503 | **0.2793 / 0.2140 / 0.0528** |
| mean std | 4.94 | 5.19 |
| `low_pick_8` top | 3.6× | **2,000×** (sd 0.80 → 1.73) |
| `low_pick_7` top | 67.1× | **1,000×** |
| `classic_pick_8` top | 599.9× | **3,500×** |
| `high_pick_8` top / std | 4,699.8× / 18.31 | **6,000× / 18.29** |
| `high_pick_5` Off std | 17.59 | **18.18** |
| worst std | 18.74 (`high_pick_10_earn`) | **18.74** (untouched) |

Two Earn pick-4 modes crossed 1× when the water-fill clawed mid rows to pay for
the pin — the entire mean win / LDW / push move:

- `low_pick_4_earn`: win 30% → 70%, LDW 40% → 0, push 0 → 40%. The refund row
  became a honest push; zero-LDW modes 80 → 81.
- `medium_pick_4_earn`: win 8.7% → 4.9%, LDW 16.9% → 20.7%. A paying row dropped
  under 1×.

Unlike 9–10, this pass *can* change session feel, but only on those two Earn
pick-4 tables. Hard failures 0. `high_pick_10_earn` remains the most volatile
mode; `high_pick_5` Off is now the highest *unflagged-looking* std at 18.18.
