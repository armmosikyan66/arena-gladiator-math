---
type: index
tags: [meta]
updated: 2026-09-01
source_count: 7
page_count: 21
last_change: 2026-09-01 keno paytable generation algorithm (concepts/keno-paytable-generation).
---

# Math SDK Wiki

LLM-maintained knowledge base for the Stake Engine Math SDK in `math/`. Official
vendor docs stay in `math/docs/` — this wiki synthesizes **this repo**.

**How to use**

- Browse by category. Every page has YAML frontmatter and `[[wikilinks]]`.
- `log.md` records ingest / query / lint.
- Schema: `math/AGENTS.md`. Skills: `math-sdk`, `math-wiki`, `keno-math`.

**Common asks**

- _"Ingest this math/docs page"_
- _"What do we know about books / LUT / publish?"_
- _"Lint the math wiki"_
- _"File this conversation back into the wiki"_

---

## Sources

_Vendor and external docs, summarized — not copied._

- [[sources/stake-engine-math-sdk]] — Official Math SDK wiki (`math/docs/`, MkDocs).
- [[sources/tower-math-rating-limits]] — Tower math agent brief: 3-Star envelope, survival→multipliers, fail-closed validation.
- [[sources/keno-xtreme-analysis]] — Stake Keno Xtreme docx: probabilities match luma-keno exactly; no multiplier values in the docx; 3.50% house edge (page claim).
- [[sources/keno-xtreme-easy-hud]] — Keno Xtreme Easy in-game HUD: pick 1–10 hit multipliers, ~99% RTP, 0.1× lattice traps.
- [[sources/keno-xtreme-classic-hud]] — Keno Xtreme Classic HUD: pick 1–10 hit multipliers, 42–91% RTP on picks 2–10.
- [[sources/keno-xtreme-medium-hud]] — Keno Xtreme Medium HUD: pick 1–10; pick 3 is 115% RTP at 75×.
- [[sources/keno-xtreme-hard-hud]] — Keno Xtreme Hard / Degen HUD: pick 10 = 50,000×; picks 2–6 player-favor.

## Codebase

- [[codebase/sdk-layout]] — `src/`, `games/`, outputs, what to edit.
- [[codebase/gladiator-tower]] — Session climb math, modes, publish pipeline.
- [[codebase/luma-keno]] — Hit-count keno, 160 modes (Off / Earn / buy10 / buy100) at 0.9650 RTP; `pulseRolled` vs `pulse`; buy ceilings capped per cost. Off `low` **is** the snapped Keno Xtreme Easy copy (2026-09-01, `easy_off_low.py`); classic / medium / high HUDs still not copied.

## Domain

- [[domain/stake-engine-publish]] — Books, LUT, `index.json`, payout units, RGS.
- [[domain/stake-rating-limits]] — 2-Star / 3-Star gates (P5K, P10K, CVaR, ETL, ETL sum, stddev, caps). Max payout is measured against the **base bet**, so bonus-buy cost divides the usable ceiling. Volatility is also rated categorically, and a mode can be rated Extreme at half the stddev ceiling. ETL sum (etl40+etl10k) is a separate dashboard gate: 1.3 / 1.5.
- [[domain/keno-xtreme-easy]] — Keno Xtreme Easy pick 1–10 hit multipliers (HUD) + the shipped luma-keno Off `low` snap (0.9635–0.9653).
- [[domain/keno-xtreme-classic]] — Keno Xtreme Classic pick 1–10 hit multipliers (HUD).
- [[domain/keno-xtreme-medium]] — Keno Xtreme Medium pick 1–10 hit multipliers (HUD).
- [[domain/keno-xtreme-hard]] — Keno Xtreme Hard / Degen pick 1–10 hit multipliers (HUD).

## Concepts

- [[concepts/wiki-maintenance-workflow]] — Ingest, query, lint, logging.
- [[concepts/tower-math-from-ratings]] — Build order: probabilities → RTP budget → row table → MC.
- [[concepts/keno-paytable-generation]] — How Off multipliers are solved: RTP identity, 0.1× lattice, classic geometric ladder, low leftover-share, pick_1 two-outcome lattice.

## Analyses

- [[analyses/rating-limit-contradictions]] — Brief vs `rgs_verification.py` vs current ladder.
