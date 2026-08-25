# Math SDK wiki map

Official Stake Engine docs live in `math/docs/` (MkDocs nav: `math/mkdocs.yml`).
Do not copy these pages into `math/wiki/` — summarize and link.

Project wiki (`math/wiki/`) holds repo-specific facts (Gladiator Tower, publish
quirks). Skill `math-wiki` owns that layer.

## Entry

| Page | When to read |
| --- | --- |
| `math/docs/math_home.md` | What the Math SDK is and why books exist |
| `math/docs/index.md` | Stake Development Kit overview (math + frontend + RGS) |
| `math/docs/math_docs/general_overview.md` | Install (Python ≥ 3.12, `make setup`, Rust for optimizer) |
| `math/docs/math_docs/quickstart.md` | First `make run`, debug 100 sims, production batch |
| `math/docs/math_docs/directory.md` | `src/` / `games/` / `utils/` / `optimization_program/` |

## Architecture

| Page | When to read |
| --- | --- |
| `math/docs/math_docs/overview_section/state_overview.md` | GameState, books, LUT weight = 1 then optimize |
| `math/docs/math_docs/overview_section/game_struct.md` | Required game files + `create_books` / `generate_configs` |
| `math/docs/math_docs/overview_section/game_format.md` | New-game walkthrough: config, `run_spin`, `run.py` |

## Gamestate

| Page | When to read |
| --- | --- |
| `math/docs/math_docs/gamestate_section/repeat_info.md` | Distribution quotas + `self.repeat` / `check_repeat` |
| `math/docs/math_docs/gamestate_section/configuration_section/config_overview.md` | Paytable, reels, special symbols, FS triggers |
| `math/docs/math_docs/gamestate_section/configuration_section/betmode_overview.md` | `auto_close_disabled`, `is_feature`, `is_buybonus` |
| `math/docs/math_docs/gamestate_section/configuration_section/betmode_dist.md` | `reel_weights`, force flags |
| `math/docs/math_docs/gamestate_section/syms_board_section/symbol_info.md` | Symbol attributes |
| `math/docs/math_docs/gamestate_section/syms_board_section/board_info.md` | Board layout |
| `math/docs/math_docs/gamestate_section/win_info.md` | WinManager |
| `math/docs/math_docs/gamestate_section/events_info.md` | Event contract with frontend |
| `math/docs/math_docs/gamestate_section/force_info.md` | `self.record()` / force JSON |

## Source (`math/src/`)

| Page | Code |
| --- | --- |
| `source_section/board_info.md` | `src/calculations/board.py` |
| `source_section/tumble_info.md` | `src/calculations/tumble.py` |
| `source_section/lines_info.md` | `src/calculations/lines.py` |
| `source_section/ways_info.md` | `src/calculations/ways.py` |
| `source_section/scatter_info.md` | `src/calculations/scatter.py` |
| `source_section/cluster_info.md` | `src/calculations/cluster.py` |
| `source_section/config_info.md` | `src/config/` |
| `source_section/event_info.md` | `src/events/events.py` |
| `source_section/executables_info.md` | `src/executables/executables.py` |
| `source_section/state_info.md` | `src/state/` |
| `source_section/win_manager.md` | `src/wins/win_manager.py` |
| `source_section/file_info.md` | books, LUTs, configs, paths |

## Publish / RGS

| Page | When to read |
| --- | --- |
| `math/docs/rgs_docs/data_format.md` | `index.json`, LUT CSV, `.jsonl.zst`, required book keys |
| `math/docs/rgs_docs/RGS.md` | Wallet APIs, 6-decimal money, session URL params |
| `math/docs/books_formatting.md` | `make run` pretty-prints uncompressed JSONL |
| `math/docs/math_docs/uploads_section/upload_info.md` | AWS / ACP upload helpers |
| `math/docs/math_docs/optimization_section/optimization_algorithm.md` | Rust LUT optimizer |

## Samples and extras

| Page | When to read |
| --- | --- |
| `math/docs/math_docs/sample_section/sample_games.md` | lines / ways / cluster / scatter / expwilds |
| `math/docs/math_docs/utils_section/utilities.md` | PAR sheets, decompress, LUT swap, hashes |
| `math/docs/simple_example/simple_example.md` | Minimal frontend ↔ RGS |

## Project wiki (rating / tower)

| Page | When to read |
| --- | --- |
| `math/wiki/domain/stake-rating-limits.md` | 2-Star / 3-Star gates, CVaR, ETL, metric mapping |
| `math/wiki/concepts/tower-math-from-ratings.md` | Survival → RTP budget → row table → MC |
| `math/wiki/analyses/rating-limit-contradictions.md` | Brief vs `rgs_verification.py` vs live ladder |
| `math/raw/tower-game-math-engine-agent-context.md` | Ingested product brief |

Frontend SDK wiki (same MkDocs site, not math engine): `math/docs/fe_docs/`,
`math/docs/fe_home.md`.
