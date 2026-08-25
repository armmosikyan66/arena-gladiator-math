---
type: analysis
tags: [rating, validation, contradiction]
updated: 2026-08-24
---

# Rating-limit contradictions

Filed while ingesting [[sources/tower-math-rating-limits]]. Do not silently
pick a side — surface both until ACP/verif.md is confirmed.

## 1. 3-Star tail gates vs local verifier

| Gate | Product brief (3-Star) | `verify_mode_volatility` (comment: 3-star) |
| --- | --- | --- |
| P5K | ≤ 0.050 | ≤ 0.010 |
| P10K | ≤ 0.010 | ≤ 0.005 |

The local function matches the brief’s **2-Star** tail gates. Generating to
the brief’s 3-Star room can **warn** in `rgs_verification.py`. Until ACP is
confirmed, stay under the **intersection** (tighter numbers) so publish can
succeed.

`verify_mode_volatility` **warns**; the brief **fails the build**. Skill
policy: treat verifier violations as build failures.

## 2. Empty SOURCE LIMITS table

The paste had no Section 2 numbers. CVaR 800, ETL 0.9/0.8, max payout
100,000×, cost multiplier 1,500, base stddev 0.6–60 come from Stake-tool
verif.md + this repo, not from the brief. Marked `?` until an official
table is dropped in `math/raw/`.

## 3. Current tower ladder vs survival construction

[[codebase/gladiator-tower]] still uses fair-odds × depth house edge
(`game_calculations.build_row_steps`). The brief forbids arbitrary row
factors and requires P_k → m_k. Existing published ladders are **legacy**
until regenerated under [[concepts/tower-math-from-ratings]].

## 4. Exposure vs maxWinning

The brief says do not reinterpret exposure as a payout-multiplier cap
unless the risk engine defines it that way. This repo caps cashout at
`$10,000` (`DEFAULT_MAX_PAYOUT`). Confirm whether ACP “max exposure” is
that dollar cap, concurrent open-session liability, or something else.

## 5. Quality stars vs math stars

Stake **quality** ranking (0–3 stars from reviewers) is a different system
from this **math risk** envelope. Do not mix them.
