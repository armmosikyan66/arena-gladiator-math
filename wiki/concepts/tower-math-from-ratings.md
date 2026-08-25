---
type: concept
tags: [tower, rtp, survival, validation]
updated: 2026-08-24
---

# Tower math from rating constraints

How to **build** Gladiator Tower math (from [[sources/tower-math-rating-limits]]).
Limits: [[domain/stake-rating-limits]].

## Order (mandatory)

```
rating + target RTP
  → outcome space (loss, cashout-at-k, top, bonus products)
  → allocate p across core / tail / extreme tail  (leave margin)
  → solve m from RTP_budget / p  (never the reverse)
  → derive row table from survival P_k
  → analytical metrics
  → seeded Monte Carlo
  → pass/fail every gate  → export or regenerate
```

Do not start from a desired visual ladder. Do not clamp after a failed
validation.

## Survival → row multipliers

Let `q` = P(safe pick | row) from geometry (`win_count / cols`).
P_0 = 1. P_{k+1} = P_k × q (play-to-row model; adjust if early cashout is
in the outcome space).

A reference cashout multiplier at row k satisfies contribution
`P_k × m_k` within that row’s RTP budget, then bonuses and the rating
ceiling. Store per row: index, P_survive, P_fail, m, cumulative RTP,
bonus modifier.

Forbidden: `m_k = m_{k-1} × arbitrary_step`.

> ⚠️ Contradicts current [[codebase/gladiator-tower]]:
> `step[i] = fair × (1 − (0.01 + i × 0.002))` then `coefficient *= step`.
> New math must follow survival → RTP budget. Do not extend the old ladder
> without re-solving.

## Validation

Analytical formulas are not enough. For every released math version and
every bet-size regime:

1. Fixed validation seed.
2. Sample size large enough to estimate P5K / P10K with margin.
3. Report RTP, stddev, CVaR, tail probs, ETL, max payout, exposure.
4. **Fail the build** if any hard gate fails (`rgs_verification.py` today
   only **warns** — treat those warnings as failures when generating math).

## Required agent output

Machine-readable + human-readable: rating, target RTP/edge, outcome table,
per-row multiplier table, RTP by zone, P(40×)/P5K/P10K, stddev, CVaR,
ETL, max payout, max liability, MC n/seed, pass/fail per constraint.
