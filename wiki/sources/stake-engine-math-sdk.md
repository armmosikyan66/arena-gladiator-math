---
type: source
tags: [stake-engine, math-sdk, vendor]
title: Stake Engine Math SDK wiki
author: Stake Engine
date_ingested: 2026-08-24
source_path: math/docs/
updated: 2026-08-24
---

# Stake Engine Math SDK (vendor wiki)

Official MkDocs site checked into `math/docs/` (nav: `math/mkdocs.yml`). Hosted
at https://stakeengine.github.io/math-sdk/. Do not duplicate chapters here —
use the skill map `math/.cursor/skills/math-sdk/wiki-map.md`.

## Durable facts (from `math/docs/`)

- All published outcomes are **static**. RGS samples a LUT row and returns that
  book's `events` on `/wallet/play` (from `math/docs/math_home.md`,
  `math/docs/index.md`).
- Required publish files: `index.json`, lookup CSV (`id, weight, payout`),
  zstd JSONL books. Book keys: `id`, `events`, `payoutMultiplier`
  (from `math/docs/rgs_docs/data_format.md`).
- `payoutMultiplier` in files is the float multiplier × 100 as int (11.5× →
  1150). Wallet money is a **different** scale: 6 decimal places
  (`1000000` = $1) (from `math/docs/rgs_docs/RGS.md`).
- Games live under `games/<id>/`; shared engine in `src/`. Entry is `run.py` →
  `GameState.run_spin` (from `math/docs/math_docs/overview_section/game_struct.md`).
- Distribution quotas pre-assign criteria to sim ids; `repeat` / `check_repeat`
  rejects spins that miss the assigned bucket
  (from `math/docs/math_docs/gamestate_section/repeat_info.md`).
- Setup: Python ≥ 3.12, `make setup`; Rust/Cargo for the LUT optimizer
  (from `math/docs/math_docs/general_overview.md`).

## Related

- [[codebase/sdk-layout]]
- [[domain/stake-engine-publish]]
- [[codebase/gladiator-tower]]
