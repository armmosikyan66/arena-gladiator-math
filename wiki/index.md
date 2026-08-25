---
type: index
tags: [meta]
updated: 2026-08-24
source_count: 2
page_count: 10
last_change: 2026-08-24 Ingested tower rating-limit brief; 3-Star is the default math envelope.
---

# Math SDK Wiki

LLM-maintained knowledge base for the Stake Engine Math SDK in `math/`. Official
vendor docs stay in `math/docs/` — this wiki synthesizes **this repo**.

**How to use**

- Browse by category. Every page has YAML frontmatter and `[[wikilinks]]`.
- `log.md` records ingest / query / lint.
- Schema: `math/AGENTS.md`. Skills: `math-sdk`, `math-wiki`.

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

## Codebase

- [[codebase/sdk-layout]] — `src/`, `games/`, outputs, what to edit.
- [[codebase/gladiator-tower]] — Session climb math, modes, publish pipeline.

## Domain

- [[domain/stake-engine-publish]] — Books, LUT, `index.json`, payout units, RGS.
- [[domain/stake-rating-limits]] — 2-Star / 3-Star gates (P5K, P10K, CVaR, ETL, stddev, caps).

## Concepts

- [[concepts/wiki-maintenance-workflow]] — Ingest, query, lint, logging.
- [[concepts/tower-math-from-ratings]] — Build order: probabilities → RTP budget → row table → MC.

## Analyses

- [[analyses/rating-limit-contradictions]] — Brief vs `rgs_verification.py` vs current ladder.
