# Keno paytable design and 3-Star gates

Default rating: **3-Star**. Numbers live in skill `math-sdk` →
`rating-limits.md`. Until ACP confirms looser tails, pass the
**intersection** with `utils/rgs_verification.py` (P5K ≤ 0.010,
P10K ≤ 0.005, CVaR ≤ 800, ETL40 ≤ 0.9, ETL10k ≤ 0.8, stddev ≤ 60,
max payout 100,000×, and repo flag RTP > 0.967 as a violation).

A rating is a ceiling. Leave margin.

## Construction order

1. Load rating + target RTP (same for every pick size).
2. Fix `N=80`, `K=20`, `k ∈ {1..10}` (and risk tables if any).
3. For each k, mark which hit counts pay 0 (usually low h).
4. Split leftover RTP across paying hits (core / tail). Keep unused
   tail budget so P5K/P10K/CVaR are not sitting on the gate.
5. `m_h = RTP_h / P(h)`. Round to **0.1×**. Recompute exact RTP
   with integer `w(h)` (see [hypergeometric.md](hypergeometric.md)).
6. Analytical rating metrics — **no Monte Carlo**.
7. If any gate fails: change `m_h` or which hits pay, regenerate.
   Never clamp a published prize after the fact.

## Per-pick table (required artifact)

For each k and h: `P(h)`, `w(h)`, `m_h`, `rtp_h = P(h)*m_h`,
cumulative RTP. Plus mode-level: RTP, hit rate, stddev, CVaR,
ETL40, ETL10k, P5K, P10K, max m, pass/fail per constraint.

## Rounding

`payoutMultiplier = int(round(m * 100))` must be a multiple of 10.
Non-zero LUT payouts `< 10` (i.e. `< 0.1×`) fail format checks.

## Mode RTP gap

Dashboard **Cross-Mode RTP Consistency** is **0.50pp** (binding). Local
`rgs_verification` only warns at **5pp** (0.05 RTP). Pick sizes and risk
skins must share LUT EV; they only reshape variance.

pick_1 on a 0.1× two-outcome lattice cannot sit at ~0.966 (next step is
0.975 > 0.967 cap). luma-keno targets **0.950 on every mode** so
Cross-Mode stays under 0.50pp. One multiplier per hit. low_pick_1 is
0.5/2.3 (std ~0.78) — 0.6/2.0 sits on the 0.60 STD floor.

## Binding constraints

| Gate | Keno note |
| --- | --- |
| Max payout | Set from leftover RTP on `h=k`, not a headline 10k× |
| P5K / P10K | Zero unless some `m_h ≥ 5000` / `10000`. Prefer keeping the top prize below 5,000× unless the product requires it **and** `P(m≥5000)` still fits |
| stddev | Pick-1 can be too *quiet* (min 0.6 when cost=1). Pick-10 high-risk can exceed 60 |
| CVaR / ETL | Dominated by the two or three highest `h` on the largest k |
| Unique payouts | Natural for k≥2. If a table is degenerate (one paying value), add a real extra prize tier — do not fake ±0.1× jitter that changes advertised odds |

## Do not copy tower jitter

Tower settle modes are a single payout, so they jitter ~1% of books by
±0.1× for Stake stats. Keno modes already have a hit distribution.
Do **not** jitter advertised `pay[h]` (that silently changes posted odds).
Do **not** split miss weight to raise pick_1 RTP — one prize per hit.

## Script

```sh
python3 .cursor/skills/keno-math/scripts/rtp.py paytable.json
```

JSON shape:

```json
{
  "pool": 80,
  "drawn": 20,
  "rtp_target": 0.96,
  "picks": {
    "1": { "0": 0, "1": 3.0 },
    "10": { "0": 0, "5": 4, "10": 1000 }
  }
}
```

Omitted hit keys default to 0.
