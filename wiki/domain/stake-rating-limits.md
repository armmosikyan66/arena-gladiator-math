---
type: domain
tags: [stake-engine, rating, validation, cvar, etl]
updated: 2026-08-31
---

# Stake rating limits (math validation)

Hard envelope for Gladiator Tower math. Preferred rating: **3-Star**
(from [[sources/tower-math-rating-limits]]). Skill: `math-sdk` →
`rating-limits.md`.

Do not optimize only for the highest multiplier. Tail probability, RTP
contribution of the tail, stddev, CVaR, exposure, and ETL are all
constraints.

## 3-Star vs 2-Star (this project)

| Metric | 2-Star | 3-Star (default) | Binding source |
| --- | --- | --- | --- |
| P(X ≥ 5,000×) | ≤ 0.010 | ≤ 0.050 | product brief |
| P(X ≥ 10,000×) | ≤ 0.005 | ≤ 0.010 | product brief |
| CVaR / bet (worst 0.1% tail) | ≤ 700 | ≤ 800 | Stake-tool verif.md; repo uses 800 |
| ETL > 40× cost (RTP share / contrib) | ≤ 0.8 | ≤ 0.9 | verif.md; `rgs_verification` 0.9 |
| ETL > 10,000× | ≤ 0.6 | ≤ 0.8 | verif.md; repo 0.8 |
| ETL sum (etl40 + etl10k) | ≤ 1.3 | ≤ 1.5 | dashboard 2026-08-31. Wins ≥10,000× the **base bet** sit in both, so the sum can fail while each piece passes |
| Base stddev (costMultiplier = 1) | 0.6–50 | 0.6–60 | verif.md; dashboard Base Mode STD treats 0.60 as a failing equality — leave margin (luma-keno `STD_MIN=0.62`) |
| Max payout multiplier | 25,000× ⚠️ | 100,000× | verif.md; dashboard |
| Max cost multiplier | 1,000 | 1,500 | verif.md (not max payout) |
| RTP | within product target; repo also flags RTP **> 0.967** | `rgs_verification.py` |

Always: P(X ≥ 10,000×) ≤ P(X ≥ 5,000×). Design **below** the published
maxima (engineering margin).

> ⚠️ **Max payout multiplier, 2-Star: this page says 25,000×, the live
> dashboard says 50,000×.** Observed on the luma-keno upload, 2026-08-28: the
> Max Payout Multiplier panel reported `490,000 / 50,000` for 2-Star and
> `490,000 / 100,000` for 3-Star. Both figures are recorded rather than
> reconciled — until verif.md is re-confirmed, treat 25,000× as the
> conservative planning number and 50,000× as what the tool actually enforces.

Note the direction: for max payout the **3-Star limit is the looser one**
(100,000× vs 50,000×), because a higher rating tolerates more volatility. A mode
over the 2-Star figure is not broken, it is simply outside the 2-Star envelope —
so a 3-Star game may legitimately show 2-Star failures on this metric alone.

### Max payout is measured against the base bet

This is the one gate that is **not** normalized by `bet_cost`, which makes it the
only one a bonus-buy mode can breach while every per-cost metric looks healthy.
luma-keno's buy100 chip scales its rows by its cost on export, so a top row worth
4,900× *what the player actually staked* — the same ceiling Earn has — reported as
490,000× the base bet and failed 15 modes at 2-Star and 9 at 3-Star.

Two consequences worth keeping:

- A chip costing `c` divides its usable ceiling by `c`. luma-keno now caps the
  settled ladder at `MAX_PAYOUT_ABS[cost] / cost` in `solve_paytables.py`
  (45,000× for buy10, 90,000× for buy100, both ~10% under the tier they answer
  to). See [[codebase/luma-keno]].
- The cap must lower the risk ceiling the cap-fraction ladder steps down from,
  **not** clamp each tier to the same number. Clamping flattens the top tiers
  onto one value and the water-fill then has to break the cap to keep payouts
  strictly increasing.

> ⚠️ `rgs_verification.py` computed `max_win` and stored it on the stats object
> but omitted it from `mode_limits`, so this gate had **no local equivalent** and
> a 490,000× ladder passed the verifier cleanly before failing the dashboard.
> Added 2026-08-28. `max_win` there is the raw LUT payout — the multiplier × 100
> — so the 3-Star limit is written `100_000 * 100`.

### Volatility is also rated categorically, not just gated

Separate from the 0.6–50/60 numeric range, the dashboard's Detailed Metrics panel
prints a **volatility label** — observed value `EXTREME` — beside the number, on a
gauge that reads 0–50. The label is the softer signal of the two: a mode can sit
well inside the numeric range and still be rated Extreme.

Observed on luma-keno, 2026-08-28: `high_pick_6` (Off) showed
`VOLATILITY 25.73 — EXTREME`, exactly its base stddev, so the rating is derived
from `std` alone. 25.73 is only half the 2-Star ceiling of 50, so **passing the
stddev gate does not mean passing the rating.**

> ⚠️ unverified: the label thresholds are not published in verif.md, the Math SDK
> docs, or this wiki. The SDK's own volatility control is `min_m2m`/`max_m2m`
> (mean-to-median), which is not what the panel displays. Only one data point is
> pinned — 25.73 → Extreme. Every other luma-keno mode sits at 11–18.3 and none
> was flagged, so the Extreme boundary lies somewhere in (18.3, 25.73].

The practical lever is the **top row**, because it contributes `p(top) · m²` to
variance. `p` falls roughly 15× per pick while the ceiling rises, so that product
peaks mid-ladder rather than at the largest pick — for luma-keno's high risk it is
94% of variance at pick 6, 56% at pick 7 and 4% at pick 8. Capping the ceiling
therefore buys a large volatility cut for no change in hit rate, since the set of
paying tiers is untouched and the freed RTP redistributes across mid rows. See
`TOP_OVERRIDE` in [[codebase/luma-keno]].

> ⚠️ [[analyses/rating-limit-contradictions]]: `verify_mode_volatility` is
> labeled 3-star but uses P5K ≤ 0.01 and P10K ≤ 0.005 (the brief’s
> **2-Star** tail gates). Until ACP/verif.md is confirmed, generated math
> must pass **both** the brief and `rgs_verification.py` (intersection).

## Engine metric definitions (this repo)

Do not invent meanings. Map to `math/utils/analysis/distribution_functions.py`
and `math/utils/rgs_verification.py`:

| Brief name | Code | Definition |
| --- | --- | --- |
| Base standard deviation | `std` from `get_distribution_moments` | sqrt(Var(m)) in multiplier units; `/ bet_cost` also computed |
| CVaR per-stake | `cvar` | E[m \| m in worst 0.1% tail] / bet_cost (`cutoff=0.999`) |
| CVaR absolute | `cvar * bet` | same tail expectation in money |
| ETL > 40× | `etl40b` | Σ p_i m_i for m_i ≥ 40 × bet_cost |
| ETL > 10,000× | `etl10k` | Σ p_i m_i for m_i ≥ 10,000× the **base bet** (not `/ bet_cost` before the cutoff) |
| ETL sum | `etl_sum` = etl40 + etl10k | Dashboard gate. **1.300 (2-Star) / 1.500 (3-Star)**. Confirmed 2026-08-31 on luma-keno `high_pick_4_buy100` (1.533 / 1.500). Local solver `GATES["etl_sum"]=1.45`; `rgs_verification` 1.5 |
| Max cost multiplier | BetMode `cost` | bonus-buy / mode cost; **≠** max payout |
| Max payout multiplier | `max_win` from `verify_lookup_format` | largest LUT payout, as multiplier × 100. Against the **base bet**, never `/ bet_cost` |
| Exposure | today: `maxWinning` dollars (`DEFAULT_MAX_PAYOUT`) | **?** brief forbids silently equating exposure to a payout cap unless the risk engine does |

Cost-scaled tail probabilities: `get_prob_scale(bet_cost)` relaxes P5K/P10K
for high-cost modes (c≥1000 → ×0.2, ≥500 → ×0.5, ≥200 → ×0.8).

LUT format gates (fail before stats): payout uint, non-zero ≥ 10, **multiple
of 10**, weights uint64, Σ weights ≤ uint64 max.

## Related

- [[concepts/tower-math-from-ratings]]
- [[codebase/gladiator-tower]]
- [[domain/stake-engine-publish]]
