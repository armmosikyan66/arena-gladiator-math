---
type: domain
tags: [stake-engine, rating, validation, cvar, etl]
updated: 2026-08-25
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
| Base stddev (costMultiplier = 1) | 0.6–50 | 0.6–60 | verif.md; dashboard Base Mode STD treats 0.60 as a failing equality — leave margin (luma-keno `STD_MIN=0.62`) |
| Max payout multiplier | 25,000× | 100,000× | verif.md |
| Max cost multiplier | 1,000 | 1,500 | verif.md (not max payout) |
| RTP | within product target; repo also flags RTP **> 0.967** | `rgs_verification.py` |

Always: P(X ≥ 10,000×) ≤ P(X ≥ 5,000×). Design **below** the published
maxima (engineering margin).

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
| ETL > 10,000× | `etl10k` | Σ p_i m_i for m_i ≥ 10,000 |
| ETL sum | etl40 + etl10k unless ACP defines otherwise | **?** confirm before treating as a separate gate |
| Max cost multiplier | BetMode `cost` | bonus-buy / mode cost; **≠** max payout |
| Exposure | today: `maxWinning` dollars (`DEFAULT_MAX_PAYOUT`) | **?** brief forbids silently equating exposure to a payout cap unless the risk engine does |

Cost-scaled tail probabilities: `get_prob_scale(bet_cost)` relaxes P5K/P10K
for high-cost modes (c≥1000 → ×0.2, ≥500 → ×0.5, ≥200 → ×0.8).

LUT format gates (fail before stats): payout uint, non-zero ≥ 10, **multiple
of 10**, weights uint64, Σ weights ≤ uint64 max.

## Related

- [[concepts/tower-math-from-ratings]]
- [[codebase/gladiator-tower]]
- [[domain/stake-engine-publish]]
