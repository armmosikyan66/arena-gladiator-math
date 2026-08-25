# Game files and spin loop

Copy `math/games/template/` (or the closest sample under `math/games/`).
`library/` is created by the engine.

```
games/<id>/
  run.py
  game_config.py
  gamestate.py
  game_override.py
  game_executables.py
  game_calculations.py
  game_events.py
  game_optimization.py
  readme.txt
  reels/                 # BR0.csv, FR0.csv, …
  library/               # generated
```

## Class MRO

`GameState` (gamestate.py) subclasses `GameStateOverride`, which subclasses
calculations/executables down to `src/state/state.py`. Override the earliest
class that owns the behavior:

- `game_override.py` — `reset_book`, seed, book-local fields
- `game_executables.py` — draw board, emit wins, freespin helpers
- `game_calculations.py` — one-off math (ladders, bonuses, cluster extras)
- `game_events.py` — functions that `book.add_event(...)` (not mixed into calc)

## `run_spin` (required)

```python
def run_spin(self, sim, simulation_seed=None):
    self.reset_seed(sim)
    self.repeat = True
    while self.repeat:
        self.reset_book()
        self.draw_board()
        # evaluate wins → WinManager → emit events
        self.win_manager.update_gametype_wins(self.gametype)
        if self.check_fs_condition():
            self.run_freespin_from_base()
        self.evaluate_finalwin()
        self.check_repeat()
    self.imprint_wins()
```

`reset_book()` sets `repeat = False`. `check_repeat()` sets it True again if
the assigned Distribution criteria (0-win, freegame, wincap, …) were not met.

## `GameConfig`

Fill every `Config` field explicitly. Symbols must appear in `paytable` or
`special_symbols` or reel load raises. Paytable keys: `(kind: int, name: str)`.

```python
self.paytable = {(3, "L1"): 10, (4, "L1"): 25, (5, "L1"): 100}
self.special_symbols = {"wild": ["W"], "scatter": ["S"]}
self.freespin_triggers = {
    self.basegame_type: {3: 10, 4: 15, 5: 20},
    self.freegame_type: {2: 4, 3: 6},
}
```

## BetMode + Distribution

Quotas for one mode must sum to 1. Criteria are assigned to sim ids **before**
threads run (so max-win work is not left to the last thread). Optimizer
condition order is exclusive — list `wincap` before `freegame`.

```python
BetMode(
    name="base",
    cost=1.0,
    rtp=self.rtp,
    max_win=self.wincap,
    auto_close_disabled=False,  # True = FE must /wallet/end-round
    is_feature=True,
    is_buybonus=False,
    distributions=[
        Distribution(criteria="wincap", quota=0.001, win_criteria=self.wincap,
                     conditions={"force_wincap": True, "force_freegame": True, ...}),
        Distribution(criteria="freegame", quota=0.1,
                     conditions={"force_freegame": True, ...}),
        Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions={...}),
        Distribution(criteria="basegame", quota=0.5, conditions={...}),
    ],
)
```

`num_sim_args` keys in `run.py` must match BetMode `name`s.

## Win types (`self.win_type`)

| Value | Engine | Notes |
| --- | --- | --- |
| `lines` | `src/calculations/lines.py` | Paylines in config |
| `ways` | `ways.py` | Left-to-right ways |
| `scatter` | `scatter.py` | Pay-anywhere |
| `cluster` | `cluster.py` | Usually + tumble |
| `other` | game code | Tower / non-slot (this repo) |

Tumble/cascade: `src/calculations/tumble.py` + tumble events.

## `run.py` flags

| Flag | Meaning |
| --- | --- |
| `num_sim_args` | Sims per bet mode |
| `compression` | `True` → `.jsonl.zst` for publish |
| `num_threads` / `batching_size` | Simulation parallelism |
| `run_sims` / `run_optimization` / `run_analysis` / `upload_data` | Pipeline stages |

After `create_books`, always `generate_configs(gamestate)`.

## Tower math (this repo)

Do not invent row multipliers by multiplying a previous step by an
arbitrary factor. Load 3-Star (default) limits from
[rating-limits.md](rating-limits.md), allocate probabilities, solve
`m = RTP_budget / p`, derive each row from survival P_k, then run
seeded Monte Carlo. Fail closed — never clamp.

Per row persist: index, P_survive, P_fail, multiplier, cumulative RTP,
bonus modifier. Full workflow:
`math/wiki/concepts/tower-math-from-ratings.md`.

