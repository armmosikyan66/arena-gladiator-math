---
name: math-sdk
description: >-
  Works with the Stake Engine Math SDK in math/: game configs, gamestate,
  books, lookup tables, RTP optimization, publish files, RGS events,
  2-Star/3-Star rating limits (CVaR, ETL, P5K/P10K), and math/docs wiki.
  Use when creating or editing games under math/games/, running simulations,
  generating books/LUTs, publishing to Stake Engine, tuning RTP or tail
  risk, implementing win types (lines/ways/scatter/cluster), validating
  math, or consulting the Math SDK wiki.
---

# Stake Engine Math SDK

Python engine that **precomputes every round**. The RGS does not run game logic
at play time — it samples a published book and returns that book's `events`.

SDK root: `math/` (this repo). Official wiki: `math/docs/` (MkDocs). Project
wiki: `math/wiki/`. Live game: `math/games/gladiator-tower/`.

Before changing math, read `math/wiki/index.md` and the matching page in
[wiki-map.md](wiki-map.md). Wiki maintenance: skill `math-wiki`.

**Tower math is built from rating constraints, not from a visual ladder.**
Default envelope is **3-Star**. Follow [rating-limits.md](rating-limits.md)
and `math/wiki/concepts/tower-math-from-ratings.md`. Do not ship math that
fails those gates.

## Mental model

```
run.py
  → GameConfig + GameState
  → run_spin(sim)  × N   (seeded RNG, repeat until Distribution criteria)
  → books  (JSONL events + payoutMultiplier)
  → lookup CSV  (id, weight, payout)
  → optimize weights (optional Rust)
  → library/publish_files/  → Stake Engine ACP
```

On `/wallet/play`, RGS picks a simulation id by LUT weight and returns that
book's `events`. Wallet credit uses the book's `payoutMultiplier`. Anything
not in events cannot be shown.

## Hard rules

1. **Game-specific code lives in `math/games/<id>/`.** Shared reusable logic
   goes in `math/src/`. Edit `src/` with caution — every game inherits it.
2. **Start from `math/games/template/`** (or the closest sample). Copy the
   file set; do not invent a parallel layout.
3. **Calculate → update WinManager → emit event.** Emit immediately after the
   state change (snapshot, not a later summary).
4. **`payoutMultiplier` is `int(round(float_mult * 100))`.** 1× → `100`,
   11.5× → `1150`. Keep multipliers in **0.1×** steps (integer must be a
   multiple of 10) or Stake publish fails.
5. **LUT column 3 must equal the book `payoutMultiplier`.** Mismatch →
   `ERR_MATH_OUTSIDE_RANGE`. After regen, refresh optimized
   `lookUpTable_<mode>_0.csv` from the base LUT (see gladiator-tower `run.py`).
6. **Publish bundle is `library/publish_files/`:** `index.json` +
   `books_<mode>.jsonl.zst` + `lookUpTable_<mode>_0.csv`. Upload that folder
   only — not `configs/` or the web dist.
7. **Wallet amounts are 6-decimal integers** (`1000000` = $1). That is
   separate from book multipliers (×100).
8. **`auto_close_disabled=True`** when the round must stay open (player
   choice / session). Frontend then calls `/wallet/end-round`.
9. **No client RNG for outcomes.** Mines, bonuses, boards belong in published
   books. The web client only renders events.
10. **Rating envelope (default 3-Star).** Never exceed
    [rating-limits.md](rating-limits.md): max payout, P5K/P10K, stddev, CVaR,
    ETL, cost multiplier, exposure. Solve `m` from RTP budget and
    probability; derive tower rows from survival P_k. If validation fails,
    regenerate — do not clamp. Treat `rgs_verification.py` warnings as
    build failures. Until ACP confirms the brief’s looser 3-Star tail
    gates, stay under the **tighter** local verifier (P5K 1%, P10K 0.5%).

## Directory contract

| Path | Role |
| --- | --- |
| `math/src/` | Shared engine (calculations, events, state, wins, write_data) |
| `math/games/<id>/` | One game: config, gamestate, executables, events, run.py |
| `math/games/<id>/library/` | Generated books, LUTs, configs, publish_files (gitignored) |
| `math/optimization_program/` | Rust LUT weight optimizer |
| `math/utils/` | Analytics, LUT merge, decompress, AWS upload helpers |
| `math/tests/` | Win-calculation pytest |
| `math/docs/` | Official Stake Engine wiki (MkDocs, treat as vendor source) |
| `math/wiki/` | LLM wiki — project facts, do not duplicate vendor docs |

## Game file roles

See [game-files.md](game-files.md) for MRO, `run_spin` skeleton, BetMode, and
Distribution quotas.

| File | Owns |
| --- | --- |
| `run.py` | Threads, sim counts, compression, create_books, configs, opt, upload |
| `game_config.py` | `game_id`, RTP, board, paytable, reels, `bet_modes` |
| `gamestate.py` | `run_spin` / `run_freespin` entry |
| `game_override.py` | Override `reset_book` and other `state.py` hooks |
| `game_executables.py` | Reusable action groups (draw board, emit wins, FS) |
| `game_calculations.py` | Game-only math |
| `game_events.py` | Event dicts appended to `book.events` |
| `game_optimization.py` | Rust optimizer params |
| `readme.txt` | Human rules for that game |

MRO (first wins): `GameStateOverride` → `GameCalculations` → `GameExecutables`
→ `Executables` / `State`.

## Commands

From `math/` (Python ≥ 3.12; Rust/Cargo if optimizing):

```sh
make setup                          # venv + editable install
make run GAME=<game_id>             # run.py + format uncompressed books
make test                           # pytest tests/
cd math && PYTHONPATH=".:games/<id>" python3 games/<id>/run.py
```

Debug with `compression = False`, `num_threads = 1`, ~100 sims. Production:
`compression = True`, 100k+ sims/mode when the outcome space is large.

## Standard events

Event shape: `{ "index": int, "type": str, ... }`. Types in
`math/src/events/event_constants.py`:

`reveal` · `winInfo` · `setWin` · `setTotalWin` · `finalWin` · `wincap` ·
`updateFreeSpin` · `freeSpinTrigger` · `freeSpinRetrigger` · `freeSpinEnd` ·
`enterBonus` · `tumbleBoard` · `setTumbleWin` · `updateTumbleWin` ·
`updateGlobalMult`

Custom types are allowed (tower uses `sessionStart`, `tileReveal`). Frontend
must handle every type you emit.

Append with `gamestate.book.add_event(event)`.

## Outputs

| Artifact | Purpose |
| --- | --- |
| `library/books/books_<mode>.jsonl` | Debug events (uncompressed) |
| `library/publish_files/books_<mode>.jsonl.zst` | RGS play payload |
| `lookUpTable_<mode>.csv` | `id,weight,payout` (weight starts at 1) |
| `lookUpTable_<mode>_0.csv` | Optimized weights — this is what `index.json` references |
| `lookUpTableIdToCriteria_<mode>.csv` | Which Distribution criteria that sim satisfied |
| `lookUpTableSegmented_<mode>.csv` | Base vs free win split |
| `force_record_<mode>.json` | `self.record({...})` hit tracking |
| `config.json` / `config_fe.json` / `config_math.json` | RGS / FE / optimizer |
| `index.json` | Publish manifest: mode name, cost, events file, weights file |

Book JSON keys required by RGS: `id`, `events`, `payoutMultiplier`.

## This repo: Gladiator Tower

Not a slot. Session-open modes (`easy`…`nightmare`) emit `sessionStart` +
`mineLayout` at **1×** (`payoutMultiplier` 100) with
`auto_close_disabled`. Settle modes (`{diff}_loss`, `{diff}_{n}`,
`{diff}_p{payout×100}`) are separate published books.

- Business logic (bonus roll/place) only in math (`game_calculations.py`,
  `session.py`). Web never rolls bonuses.
- Constant single-payout LUTs fail Stake stats — apply ~1% ±0.1× jitter so
  each mode has ≥3 distinct payouts.
- After sims, `run.py` syncs LUTs, writes `math_config.json`, copies it to
  `web/src/data/tower-math-config.json`, and verifies `publish_files/`.
- **New/changed ladders** must be generated per [rating-limits.md](rating-limits.md)
  (survival → RTP budget → MC). The current fair-odds×edge steps are legacy
  until regenerated. Do not raise top multipliers or bonus products past
  the rating intersection.

## Do / don't

| Do | Don't |
| --- | --- |
| Override in `games/<id>/` | Fork large chunks of `src/` into the game |
| Seed RNG with `reset_seed(sim)` | Use unseeded `random` (irreproducible books) |
| Loop `while self.repeat` then `check_repeat()` | Accept a sim that misses its Distribution criteria |
| Put unique events in `game_events.py` | Cram event JSON into calculations |
| Read `math/docs/` for engine APIs | Recite vendor docs into `math/wiki/` |
| Build from P_k → RTP budget → m_k | Draw a multiplier curve then fit probabilities |
| Fail the build on rating violations | Silently clamp payouts after validation |

## Additional resources

- Rating limits + validation: [rating-limits.md](rating-limits.md)
- Official wiki map: [wiki-map.md](wiki-map.md)
- Game file templates: [game-files.md](game-files.md)
- Keno (hit-count books, hypergeometric, FE reconstruction): skill `keno-math`
- Published docs: https://stakeengine.github.io/math-sdk/
- Engine: https://engine.stake.com/
