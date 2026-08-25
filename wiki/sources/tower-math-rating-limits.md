---
type: source
tags: [stake-engine, validation, rating, cvar, etl, tower]
title: Tower game math engine — agent context
date_ingested: 2026-08-24
source_path: math/raw/tower-game-math-engine-agent-context.md
updated: 2026-08-24
---

# Tower math rating limits (source)

Product brief for the math-generation agent. Hard design constraints, not
examples. Full text: `math/raw/tower-game-math-engine-agent-context.md`.

## Durable facts

- Preferred rating is **3-Star** unless product explicitly picks another.
  A rating is a **risk envelope**, not a target. Do not consume the full
  allowance; keep margin for rounding, discretization, and MC noise.
- Build order is fixed: outcome space → RTP budget → probability allocation
  → solve multipliers → tower progression from **survival probabilities** →
  risk metrics → validation. Do not start from a visual multiplier curve.
- RTP = Σ p_i × m_i with Σ p_i = 1. For a bucket, m = RTP_budget / p.
- Tower rows: P_k = P(reach row k). Derive m_k from RTP and P_k. Forbidden:
  m_k = previous × arbitrary row factor.
- Tail gates in this brief: 3-Star P5K ≤ 0.050, P10K ≤ 0.010; 2-Star P5K ≤
  0.010, P10K ≤ 0.005. Always P10K ≤ P5K.
- Fail-closed: if any gate fails, do not ship and do not clamp. Report the
  violated constraint, regenerate, re-run the full suite.
- Maximum Cost Multiplier and Expected Tail Liability must use the **engine
  definitions** (see [[domain/stake-rating-limits]]). Do not assume they
  equal max payout or exposure/bet.

## Gaps in the paste

Section 2 (SOURCE LIMITS table) and parts of §6 / §11 had no numbers.
Missing CVaR, stddev, payout-cap, cost-multiplier, and exposure values are
filled from `math/utils/rgs_verification.py` and published Stake-tool
verif.md defaults, marked as such on [[domain/stake-rating-limits]].

## Related

- [[domain/stake-rating-limits]]
- [[concepts/tower-math-from-ratings]]
- [[codebase/gladiator-tower]]
- [[analyses/rating-limit-contradictions]]
