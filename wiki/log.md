# Math wiki log

Parseable audit trail. Newest entries at the top.

## [2026-08-25] feat | Earn Pulse ×2 (10%)

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno pulse criteria/weights, earn retune, web HUD/board rings only when booked
- notes: Independent of extras. Does not rescue 0×. Off never rolls it. Earn tables re-solved to 0.950. pick_1 Earn books=6.

## [2026-08-25] feat | Off vs Earn separated math (80 modes)

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno 80 BetModes, paytables.json earn, web Play `_earn` suffix, keno-math SKILL/events, wiki/domain/stake-engine-publish.md
- notes: Sidebar Off keeps certified table-only 0.950 chart. Sidebar Earn is a separate chart with Lumen (medium ×2) + extras priced in. Pulse/Buy still unpublished. Cross-Mode over all 80 modes.

## [2026-08-25] feat | Lumen multiplier (step 2)

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno settle_pay / lumenBoost events / LUT payouts, web reconstruct lumenBoost HUD, keno-math events.md
- notes: Catching Lumen on a paying row ×2 classic/low, ×3 medium, ×5 high. Does not rescue 0×. RTP rises further until Step 8 retune. Pulse and Buy still unused.

## [2026-08-25] feat | Extra lights (open + count as hits)

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno extras criteria/weights, kenoCatch extraHits, web reconstructExtras + bonus pause
- notes: Extras 0 or 2 from lumen / nearMiss / luck. Total hits pay the table. Lumen multiplier, Pulse, Buy not applied. RTP will rise until Step 8 retune.

## [2026-08-25] feat | Lumen mark step 1 (visual, no payout)

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno/ (criteria `hits_{h}_lumen_{0|1}`, kenoCatch.lumenHit, LUT × h or 10-h), web reconstructLumenNumber + board mark before first light, keno-math events.md
- notes: P(lumenHit|hits=h)=h/10. pick_1 has 3 books, pick_10 has 20. Same paytable. Frontend shows marked number before reveal. Boost / extras / Pulse not applied.

## [2026-08-25] manual | Client Play wallet vs preview planRound

- summary: wiki/codebase/luma-keno.md
- touched: wiki/domain/stake-engine-publish.md, wiki/index.md
- notes: Web `getEngine().Play` uses 40 `{risk}_pick_{k}` modes. Hits from kenoCatch; FE reconstructDraw. Store must apply play.balance (demo rail stuck at 1000 if not). round.ts planRound/settleRound preview-only. Keno auto-closes on Play. Buy UI is not published math.

## [2026-08-25] fix | drop miss remainder; 0.950 all modes; low_pick_1 0.5/2.3

- summary: wiki/codebase/luma-keno.md
- touched: games/luma-keno/keno_pick_one.py, solve_paytables.py, paytables.json, library/ (40 modes, 2 books per pick_1), web keno-books.json, keno-paytables.json, types.ts TOP_PRIZE, wiki/domain/stake-engine-publish.md, wiki/sources/keno-xtreme-analysis.md, wiki/index.md, .cursor/skills/keno-math/
- notes: Dual miss 0.6×/0.7× rejected. All 40 modes RTP ~0.950 (spread ~0.10pp). low_pick_1 LUT 30@50 + 10@230, std ~0.78 (clears 0.60 floor with margin). House edge 5%. Re-upload publish_files/.

## [2026-08-25] ingest | luma-keno advertised chart vs LUT remainder

- summary: wiki/codebase/luma-keno.md
- touched: wiki/codebase/sdk-layout.md, wiki/domain/stake-engine-publish.md, wiki/sources/keno-xtreme-analysis.md, wiki/index.md, .cursor/skills/keno-math/ (SKILL, paytable, events, hypergeometric)
- new: wiki/codebase/luma-keno.md
- notes: Dashboard Cross-Mode RTP 0.50pp; pick_1 LUT 24+6 remainder at 0.965; FE panel shows advertised miss only (0.6× not 0.6×/0.7×). Mirrored skill copy under math/.cursor/skills/keno-math/.

## [2026-08-25] fix | pick_1 miss remainder (24+6) for dashboard 0.50pp

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/keno_pick_one.py, solve_paytables.py, paytables.json, game_config.py, game_calculations.py, gamestate.py, game_events.py, run.py, export_luts.py, library/ (40 modes, 3 books per pick_1), web paytable panel, keno-books.json, keno-paytables.json, wiki/domain/stake-engine-publish.md
- notes: Miss weight 30 split 24@miss + 6@miss+0.1. Classic LUT 24@40, 6@50, 10@260. pick_1 LUT RTP 0.965; picks 2–10 0.9654–0.9665. Full spread 0.15pp. rgs_verification clean. Client MIN_PICKS=1, panel shows both miss amounts.

## [2026-08-25] fix | pick_1 one payout per hit (drop miss remainder)

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/keno_pick_one.py, solve_paytables.py, paytables.json, game_config.py, game_calculations.py, gamestate.py, run.py, export_luts.py, library/ (40 modes, 2 books per pick_1), web paytable panel, keno-books.json, keno-paytables.json, wiki/domain/stake-engine-publish.md
- notes: Dual miss 0.4×/0.5× rejected. Classic miss always 0.4× (LUT 30@40, 10@260). pick_1 RTP 0.950; picks 2–10 0.9654–0.9665. Solver spread gate is picks 2–10 only (0.11pp). Full 40-mode spread 1.65pp fails dashboard 0.50pp. Client MIN_PICKS=1, one number per hit row.

## [2026-08-25] fix | Restore pick_1 at 96.5% LUT RTP with 1-pick client play

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/keno_pick_one.py, solve_paytables.py, paytables.json, game_config.py, game_calculations.py, gamestate.py, run.py, export_luts.py, library/ (40 modes), web MIN_PICKS=1, keno-books.json, keno-paytables.json, wiki/domain/stake-engine-publish.md
- notes: Single advertised pick_1 pair cannot hit 96.6% (0.950 or 0.975; 0.975>0.967). Advertised miss/hit stays on 0.950 lattice (low 0.6/2.0, classic 0.4/2.6, medium 0.2/3.2, high 0.1/3.5). Miss weight 30 split 24+6 so 6 misses pay +0.1x. LUT RTP 0.965. Hit odds exact 10/40. 40 modes, spread 0.15pp, rgs_verification clean. Client MIN_PICKS=1.

## [2026-08-25] fix | Drop pick_1 for dashboard 0.50pp RTP spread

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, game_config.py, run.py, library/ (pick_1 artifacts removed), web MIN_PICKS=2, keno-books.json, keno-paytables.json, wiki/domain/stake-engine-publish.md
- notes: Cross-Mode RTP Consistency blocked at 1.65% (limit 0.50%). pick_1 is lattice-locked at 95%; picks 2-10 stay ~96.60%. Best practice for a 96.6% product is omit pick_1 (36 modes, spread ~0.11pp). Solver SPREAD_MAX now 0.50pp.

## [2026-08-25] fix | pick_1 match prize differs by risk

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, game_config.py, library/ pick_1 LUTs+books, web/src/data/keno-books.json, keno-paytables.json, web/src/lib/keno/types.ts, copy.ts
- notes: pick_1 was one shared [0.4, 2.6] row so every risk paid 2.6x on a match. Split at the same 0.95 RTP: low 0.6/2.0, classic 0.4/2.6, medium 0.2/3.2, high 0.1/3.5.

## [2026-08-25] fix | pick_1 miss rebate 0.4x (Originals-style)

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, game_config.py, library/, web/src/data/keno-books.json, keno-paytables.json, web/src/lib/keno/types.ts, web/src/lib/keno/copy.ts, web/src/components/keno/paytable-panel.tsx, wiki/domain/stake-engine-publish.md
- notes: pick_1 0-hit now pays 0.4x (LUT 40, legal). Hit is 2.6x so RTP stays 0.95 (0.75*0.4+0.25*2.6). Claimed Keno Xtreme 0.65x miss is illegal on the 0.1x grid; 0.6x/2.0x is the legal stand-in. Hit-rate 100%. Picks 2-10 unchanged.

## [2026-08-25] fix | Restore pick_1 (Xtreme 1–10 picks)

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, game_config.py, run.py, library/, web/src/data/keno-books.json, keno-paytables.json, web/src/lib/keno/types.ts, web/src/components/keno/controls.tsx, wiki/domain/stake-engine-publish.md
- notes: Keno Xtreme and the Math SDK contract are pick_1…pick_10. pick_1 restored at [0, 3.8] / RTP 0.95 (lattice; 3.9x illegal). Picks 2–10 stay at 0.9660 with refunds. Spread 1.65pp < verifier 5pp. Client MIN_PICKS=1. 40 modes, rgs_verification clean.

## [2026-08-25] analysis | classic/low 0.5x refund tier (Stake Originals style)

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, library/ (books/LUTs regenerated), web/src/data/keno-books.json, web/src/data/keno-paytables.json, web/src/lib/keno/types.ts
- notes: Keno Xtreme docx has no multipliers; Stake Originals Low pays tiny amounts on low hits (same RTP, shape only). Added REFUND_X=0.5 on classic/low one hit below PAY_START when P(h)<=0.35. classic pick_10 start moved 5→4 so 3 hits pay 0.5x. LUT payout 50 (legal). medium/high unchanged. 36 modes still RTP 0.9654–0.9665.

## [2026-08-25] ingest+analysis | Keno Xtreme docx vs luma-keno; RTP retarget 0.95 → 0.9660

- summary: wiki/sources/keno-xtreme-analysis.md
- touched: games/luma-keno/solve_paytables.py, paytables.json, game_config.py, run.py, library/ (books/LUTs/index.json regenerated), web/src/data/keno-books.json, web/src/data/keno-paytables.json, web/src/lib/keno/types.ts, web/src/store/keno-store.ts, web/src/components/keno/controls.tsx, web/src/lib/keno/copy.ts, wiki/index.md
- notes: docx probabilities (pool 40 / drawn 10, hypergeometric) match our engine exactly (max diff 1.17e-07, print rounding). Docx has NO multiplier values ("VERIFY IN GAME" placeholders) — only structure/RTP/methodology comparable. Keno Xtreme house edge 3.50%; ours was 5.00%. To lower it: pick_1 dropped (0.1× two-outcome lattice = multiples of 0.025, jumps 0.95→0.975 which busts the 0.967 verify_mode_volatility cap and would break the 0.5pp spread gate); picks 2–10 retargeted to 0.9660. 36 modes now: RTP 0.9654–0.9665, spread 0.0011, rgs_verification clean (no warnings, no mode >0.967), house edge ~3.40%. Stale pick_1 artifacts deleted from library/.

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
