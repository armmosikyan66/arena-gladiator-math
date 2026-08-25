---
type: domain
tags: [rgs, publish, books, rtp]
updated: 2026-08-25
---

# Stake Engine publish format

Facts for publishing math to the RGS (from [[sources/stake-engine-math-sdk]],
especially `math/docs/rgs_docs/data_format.md` and `math/docs/rgs_docs/RGS.md`).

## Bundle

Upload `library/publish_files/` as one directory:

1. `index.json` — `modes[]` with `name`, `cost`, `events` (`.jsonl.zst`),
   `weights` (CSV).
2. Lookup CSV — unsigned integers: simulation id, weight, payout. Payout must
   **exactly** match the book's `payoutMultiplier`.
3. Books — zstd-compressed JSONL. Each line: `id`, `events`,
   `payoutMultiplier`.

Optimized LUT filename is typically `lookUpTable_<mode>_0.csv` (weights after
the Rust optimizer, or a copy of the base LUT if optimization is skipped).

## Units

| Quantity | Scale |
| --- | --- |
| Book / LUT `payoutMultiplier` | float win × 100 as int (1× → 100) |
| Preferred step | 0.1× so the int is a multiple of 10 |
| Wallet `/play` amount | 6 decimal places (`1000000` = $1) |

## RGS play

`/wallet/play` locks the sampled book's payout. `/wallet/end-round` pays that
book — it is not a generic refund. Keep the round open with
`auto_close_disabled` when the player still has choices (Tower). **Keno**
closes on Play (`auto_close_disabled=False`); the client credits from
`play.balance` and only calls `EndRound` if `round.active`.

Iframe gets `sessionID`, `lang`, `device`, `rgs_url` (never hardcode RGS URL).

## Dashboard publish gates (stricter than rgs_verification)

The upload dashboard enforces product-compliance limits the local verifier
only warns about. Both failed Lumen Keno's first upload (2026-08-24):

1. **Hit rate floor — non-zero win at least 1 in 50 (≥ 2%).**
   A table that pays nothing below 5-of-8 hits had a paying round every
   68.8 spins → blocked. Fix: pay a small consolation on the hit count
   that restores ≥ 2% (e.g. high_pick_8 pays 2.3× on 4 hits). Do not
   "fix" it by moving RTP from the top tier down without re-checking
   ETL40/CVaR gates.
2. **Mode RTP spread.** Dashboard **Cross-Mode RTP Consistency** is **0.50pp**
   (binding). Local `rgs_verification` only warns at **5pp**. pick_1 on the
   0.1× grid is a 2-outcome lattice (RTP 0.950 or 0.975). 0.975 busts the
   0.967 cap. luma-keno targets **0.950 on all 80 modes** (40 Off table-only
   + 40 Earn with Lumen/extras). One multiplier per hit. low_pick_1 Off is
   **0.5/2.3** so Base Mode STD (~0.78) clears the 0.60 floor with margin.
   Earn uses a separate chart so bonuses do not inflate Off. Do not split
   miss weight. See
   [[sources/keno-xtreme-analysis]] and [[codebase/luma-keno]].
3. **Base Mode STD.** Floor is **0.60×** when cost=1. Dashboard failed
   `Value: 0.60x` / `Limit: = 0.60x` — treat as strict greater-than, and
   do not sit on 0.60 (0.599/0.606 round to 0.60 and fail). luma-keno
   solver uses `STD_MIN=0.62`.

## Related

- [[codebase/gladiator-tower]]
- [[codebase/luma-keno]]
- [[domain/stake-rating-limits]]
- [[codebase/sdk-layout]]
