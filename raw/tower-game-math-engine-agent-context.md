# TOWER GAME MATH ENGINE — AGENT CONTEXT

Limits per rating, payout multipliers, tail risk, and validation requirements.

Ingested 2026-08-24 from product/agent brief. Section 2 (SOURCE LIMITS table)
was empty in the paste. Numeric envelope in the wiki merges this brief’s
explicit tail gates with `math/utils/rgs_verification.py` and published
Stake-tool verif.md defaults — see wiki/sources/tower-math-rating-limits.md.

Preferred rating for this project: **3-Star** unless product requirements
select another rating.

## Hard rules

- Never generate an outcome above the configured Maximum Payout Multiplier.
- Never exceed the selected rating’s tail probability, base stddev, CVaR,
  ETL, or exposure gates.
- P(X >= 10,000x) is a subset of P(X >= 5,000x); P10K <= P5K always.
- Do not use the entire tail allowance as the target. Keep a safety margin.
- Solve probability and multiplier together. Do not invent a high multiplier
  and then patch probabilities blindly.
- Do not invent meanings for Maximum Cost Multiplier or Expected Tail
  Liability — map to the game/risk engine definitions.
- Math must be deterministic for a fixed math version and PF/RNG model.

## Core payout model

RTP = Σ p_i × m_i. Probabilities sum to 1.0.

Construction order:

1. Define the outcome space and multiplier buckets.
2. Load target RTP / house edge.
3. Allocate probability mass across core, tail, and extreme-tail zones.
4. Solve multipliers so RTP is hit without violating rating limits.
5. Analytical checks + large Monte Carlo.
6. If validation fails, adjust and solve again. Do not silently clamp.

## Tail gates (from this brief)

- 3-Star: P(X >= 5,000x) <= 0.050 and P(X >= 10,000x) <= 0.010.
- 2-Star: P(X >= 5,000x) <= 0.010 and P(X >= 10,000x) <= 0.005.

A rating is a risk envelope, not a target distribution.

## Multiplier solving

For a bucket: m = RTP_budget / p. For several: Σ(p_i × m_i) = RTP_budget.
Do not hand-draw a visual curve and assume it is valid.

## Tower implementation

For a 9-row tower, derive each row from cumulative survival probabilities.

Let P_k = probability of reaching row k. Derive a cash-out multiplier from
the RTP target and P_k, then adjust for bonuses and rating limits.

Do not use: m_k = arbitrary previous multiplier × arbitrary row factor.
Use: survival probability → target payout → validation → multiplier table.

Per row store at minimum: index, survival probability, failure probability,
multiplier, cumulative RTP contribution, bonus modifier.

## Validation (every rating, every bet-size regime)

- max payout multiplier <= rating.maxPayoutMultiplier
- P(X >= 5,000x) <= rating.tail5000
- P(X >= 10,000x) <= rating.tail10000
- base stddev <= rating.maxBaseStdDev
- CVaR per-stake and absolute <= rating limits
- ETL (>40x), ETL (>10,000x), ETL sum <= rating limits
- exposure/liability <= rating.maxExposure (engine-defined)
- RTP within tolerance
- probabilities valid and sum to 1.0

Monte Carlo: fixed seed, enough samples for rare tails, fail the build on
any hard constraint. Do not ship or clamp failures.

## Required output

Rating, target RTP/house edge, outcome table, per-row multiplier table,
RTP by zone, tail probabilities (40x, 5,000x, 10,000x), base stddev, CVaR,
ETL metrics, max payout and max liability, MC sample size/seed, pass/fail
per constraint.
