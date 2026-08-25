# Math wiki log

Parseable audit trail. Newest entries at the top.

## [2026-08-24] analysis | Lumen Keno publish-gate failures fixed

- summary: dashboard blocked upload on two product gates stricter than rgs_verification
- touched: games/luma-keno/solve_paytables.py, paytables.json, wiki/domain/stake-engine-publish.md, web/src/data/keno-books.json, web/src/lib/keno/types.ts
- notes: (1) hit-rate floor ≥2% (1-in-50): high_pick_8 paid nothing below 5 hits (1 in 68.8) → consolation moved to 4 hits. (2) RTP spread ≤0.5pp: pick_1 on the 0.1× grid is a 2-outcome lattice (3.8×→0.95, 3.9×→0.975>0.967 cap) → game-wide target retargeted 0.96→0.95, all 40 modes converge ±0.05pp. Published LUT spread 0.0010, min hit rate 0.0258 (high_pick_6, 1 in 38.7). Solver now hard-fails on both dashboard gates.

## [2026-08-24] ingest | Tower rating limits (3-Star default)

- summary: wiki/sources/tower-math-rating-limits.md
- touched: wiki/index.md, wiki/codebase/gladiator-tower.md
- new: wiki/domain/stake-rating-limits.md, wiki/concepts/tower-math-from-ratings.md, wiki/analyses/rating-limit-contradictions.md
- notes: Paste omitted Section 2 numeric table. 3-Star tail gates in the brief (P5K 5%, P10K 1%) contradict rgs_verification.py (1% / 0.5% labeled 3-star). Current ladder is fair-odds×edge, not survival→RTP. Exposure vs maxWinning unresolved.

## [2026-08-24] ingest | Bootstrap Math SDK wiki

- summary: wiki/sources/stake-engine-math-sdk.md
- touched: wiki/index.md
- new: wiki/sources/stake-engine-math-sdk.md, wiki/codebase/sdk-layout.md, wiki/codebase/gladiator-tower.md, wiki/domain/stake-engine-publish.md, wiki/concepts/wiki-maintenance-workflow.md
- notes: Vendor docs remain in math/docs/. This layer is repo-specific. Gladiator Tower is the live game; sample slots may still exist under games/0_0_*.
