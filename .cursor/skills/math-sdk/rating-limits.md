# Stake rating limits — build constraints

Canonical numbers for generating Tower math. Wiki:
`math/wiki/domain/stake-rating-limits.md`. Brief:
`math/raw/tower-game-math-engine-agent-context.md`.

**Default rating: 3-Star.** A rating is a ceiling, not a target. Leave
margin; do not sit on the gate.

## Envelope

| Metric | 2-Star | 3-Star | Notes |
| --- | --- | --- | --- |
| `tail5000` P(X≥5,000×) | 0.010 | 0.050 | Brief. Local verifier uses 0.010 even when labeled 3-star |
| `tail10000` P(X≥10,000×) | 0.005 | 0.010 | Brief. Local verifier uses 0.005. Always ≤ P5K |
| `cvarPerStake` | 700 | 800 | CVaR of worst 0.1% tail / bet |
| `tailLiability40` ETL>40×cost | 0.8 | 0.9 | Σ p·m for m ≥ 40×cost |
| `tailLiability10000` ETL>10k× | 0.6 | 0.8 | Σ p·m for m ≥ 10,000× **base bet** |
| `tailLiabilitySum` ETL40+ETL10k | 1.3 | 1.5 | Dashboard. Wins ≥10k× sit in both; sum can fail while each piece passes |
| `maxBaseStdDev` | 50 | 60 | Also min 0.6 when costMultiplier=1 |
| `maxPayoutMultiplier` | 25,000 | 100,000 | No outcome above this |
| `maxCostMultiplier` | 1,000 | 1,500 | Mode cost; **not** max payout |

Until ACP confirms Section 2 of the brief, **generated math must pass the
intersection**: P5K ≤ 0.010, P10K ≤ 0.005, plus the 3-Star CVaR/ETL/stddev
caps and ETL sum ≤ 1.5, so `utils/rgs_verification.py` does not warn.

Repo RTP flag: `rtp > 0.967` is treated as a violation in
`verify_mode_volatility`. Product target RTP still comes from GameConfig
house edge / `sessionRtp`.

## Construction order (do not skip)

1. Load rating + target RTP / house edge.
2. Define discrete outcomes (loss, cashout-at-row, top, bonus products).
3. Allocate probability (core / tail / extreme). Keep unused tail budget.
4. Solve multipliers: `m = RTP_budget / p` (or Σ p_i m_i = budget).
5. Tower rows from survival P_k — not `m_k = m_{k-1} × arbitrary_step`.
6. Analytical metrics, then seeded Monte Carlo at every bet-size regime.
7. If any gate fails: report, regenerate, re-validate. **Never clamp.**

## Per-row table (required)

For each tower row k: `index`, `P_survive`, `P_fail`, `multiplier`,
`cumulativeRtp`, `bonusModifier`.

## Fail-closed checks

LUT format (hard): integer payouts, non-zero ≥ 10, **% 10 == 0**, uint64
weights.

Stats (treat local **warnings as failures** when generating math):

```
max(m) <= maxPayoutMultiplier
P5K <= tail5000
P10K <= tail10000
baseStd <= maxBaseStdDev
cvarPerStake <= cvarPerStake cap
etl40 <= tailLiability40
etl10k <= tailLiability10000
etl_sum <= tailLiabilitySum
exposure <= engine definition (today: maxWinning dollars — confirm)
Σ p ~= 1
RTP within tolerance
```

Run `python3 -m utils.rgs_verification -g gladiator-tower` (from `math/`
with PYTHONPATH) after books exist. Fixed MC seed required for regressions.

## Required summary output

Rating, target RTP/edge, outcome table, row multiplier table, RTP by zone,
P(40×)/P5K/P10K, stddev, CVaR per-stake and absolute, ETL metrics, max
payout, max liability, MC n + seed, pass/fail per constraint.
