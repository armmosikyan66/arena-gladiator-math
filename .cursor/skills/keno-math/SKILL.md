---
name: keno-math
description: >-
  Builds and validates Stake Engine math for keno in math/games/:
  hypergeometric hit probabilities, pick-count bet modes, hit-count books
  and LUTs, paytables, RTP, 3-Star rating gates, and frontend draw
  reconstruction. Use when creating or editing a keno game, keno paytable,
  keno books, pick-size modes, or mapping the Stake Engine Math SDK
  (stake-engine.com/docs/math) to keno instead of slots or Gladiator Tower.
---

# Keno on Stake Engine Math SDK

Keno is **not a slot**. Do not copy lines/ways/cluster/scatter samples.
Do not copy Gladiator Tower session-open / settle modes.

Official Math SDK hub: [stake-engine.com/docs/math](https://stake-engine.com/docs/math).
Technical source of truth in this repo: `math/docs/` (MkDocs). Hosted:
https://stakeengine.github.io/math-sdk/. Engine conventions: skill `math-sdk`.
Rating numbers: `math-sdk` → [rating-limits.md](../math-sdk/rating-limits.md).

Game id: `math/games/keno/` (create from `math/games/template/`).
`win_type = "other"`. Empty reels / paytable like tower config, then replace
all game logic.

## Mental model

Stake Engine **precomputes every round**. `/wallet/play` only sends
`amount`, `sessionID`, `mode` — **not** the player's spots. The RGS samples
a published book and credits that book's `payoutMultiplier`. Player-chosen
numbers cannot change the wallet after play.

So keno math publishes **hit-count outcomes**, not specific 80-ball draws:

```
player picks k spots on the client
  → POST /wallet/play  mode=pick_k   (or {risk}_pick_k)
  → RGS samples a book with hits=h and payout=paytable[k][h]
  → frontend reconstructs a 20-ball draw consistent with (picks, h)
```

Books lock **how many** of the player's numbers catch. The client invents
**which** numbers were drawn so the animation matches the player's card.

Exact probabilities: Hypergeometric(N=80, K=20, n=k). See
[hypergeometric.md](hypergeometric.md). Do **not** Monte Carlo 100k spins
and run the Rust optimizer — that destroys exact weights.

## Hard rules

1. **`win_type = "other"`.** No reelstrips, no `draw_board()`, no slot
   win evaluators.
2. **One BetMode per pick size** (and per risk table if you have several).
   Mode name is the only play-time input. Example: `pick_1` … `pick_10`.
3. **LUT weight for hit `h` is exact** `C(20,h) * C(60, k-h)`. Payout
   column is `int(round(pay(k,h) * 100))`, multiple of 10 (0.1× steps).
4. **Skip the Rust optimizer.** Copy `lookUpTable_<mode>.csv` →
   `lookUpTable_<mode>_0.csv` with those integer weights. Optimizer would
   rebalance away from true keno odds.
5. **Do not put the player's spots in the book.** Events carry `picksCount`
   and `hits` (and the paytable row). Frontend reconstructs the draw.
   See [events.md](events.md).
6. **Single-shot round.** `auto_close_disabled=False`. Emit `setWin` /
   `setTotalWin` / `finalWin`. Unlike tower, keno must **not** stay open
   for mid-round choices.
7. **Same LUT RTP on every pick-size mode.** Dashboard **Cross-Mode RTP
   Consistency** is **0.50pp** (binding). Local `rgs_verification` only
   warns at **5pp**. Design advertised tables to one target. pick_1 on
   the 0.1× lattice is 0.950 or 0.975; 0.975 busts the 0.967 cap, so
   luma-keno targets **0.950 on all 40 modes**. Do not split miss weight
   to fake a higher RTP (0.6× vs 0.7× fails Base Mode STD).
8. **3-Star envelope (default).** High-risk `pick_10` is the binding mode.
   Cap the top prize from probability, not from a marketing max. Fail
   closed — do not clamp after validation.
9. **No client RNG for the hit count.** Hits come from the book. Client
   RNG is only for reconstructing a draw that *realizes* that hit count.
10. **`payoutMultiplier` on the book root must match LUT column 3.**
    Mismatch → `ERR_MATH_OUTSIDE_RANGE`.

## Directory contract

| Path | Owns |
| --- | --- |
| `math/games/keno/game_config.py` | `game_id`, RTP, pool/draw/pick range, risk tables, BetModes |
| `math/games/keno/game_calculations.py` | `math.comb` weights, pay(k,h), RTP, rating stats |
| `math/games/keno/gamestate.py` | `run_spin`: criteria → hits → pay → events |
| `math/games/keno/game_events.py` | `kenoStart`, `kenoCatch`, win events |
| `math/games/keno/game_override.py` | `reset_book`, `check_repeat` |
| `math/games/keno/run.py` | Write exact LUTs after books; skip optimization |
| `math/src/` | Do not fork slot code into keno |

Config skeleton (empty slot fields, like tower):

```python
self.win_type = "other"
self.num_reels = 0
self.num_rows = []
self.paytable = {}          # slot paytable unused; keno pays live in calculations
self.include_padding = False
self.special_symbols = {"wild": [], "scatter": [], "multiplier": []}
self.keno_pool = 80
self.keno_drawn = 20
self.keno_picks = range(1, 11)   # inclusive
```

## `run_spin`

Criteria are assigned **before** threads run. Name them `hits_{h}` so the
spin is deterministic — no `while self.repeat` retries.

```python
def run_spin(self, sim, simulation_seed=None):
    self.reset_seed(sim)
    self.repeat = True
    while self.repeat:
        self.reset_book()
        k = self.picks_for_mode()          # from BetMode name
        h = self.hits_from_criteria()      # "hits_7" → 7
        pay = self.pay_for(k, h)           # 0.1× grid
        keno_start_event(self, k, h, pay)
        keno_catch_event(self, h)
        self.win_manager.update_spinwin(pay)
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()           # sets payoutMultiplier; emit finalWin
        self.check_repeat()                # accept if hits matched criteria
    self.imprint_wins()
```

`num_sim_args[mode] = k + 1` (one book per legal hit). Quotas may be equal;
**weights** carry the true probabilities, not quotas.

## BetMode

```python
BetMode(
    name="pick_10",          # play payload mode
    cost=1.0,
    rtp=self.rtp,            # same target as other pick sizes
    max_win=self.wincap,
    auto_close_disabled=False,
    is_feature=True,         # keep last pick-size selected
    is_buybonus=False,
    distributions=[
        Distribution(criteria=f"hits_{h}", quota=1.0 / (k + 1),
                     win_criteria=float(pay[h]),
                     conditions={"force_wincap": False, "force_freegame": False})
        for h in range(k + 1)
    ],
)
```

Risk tables (optional): `classic_pick_10`, `low_pick_10`, … — still one
LUT RTP target. High-risk changes the **shape** of `pay[h]`, not EV.

## This repo: luma-keno

`math/games/luma-keno/`. Pool **40**, drawn **10**, picks **1–10**, four
risks (`classic` / `low` / `medium` / `high`). `win_type = "other"`.
Target RTP **0.950** (house edge 5%). Skip the optimizer.

**pick_1 lattice.** Two outcomes on the 0.1× grid, `P(hit)=10/40=0.25`,
so a single miss/hit pair has RTP in steps of **0.025**: **0.950 or
0.975**. 0.975 busts `verify_mode_volatility` (0.967). One multiplier
per hit — **do not** split miss weight (0.6× vs 0.7× fails Base Mode STD
and pays two prizes for one miss). Advertised rows: low 0.5/2.3 (std
0.78, above the 0.60 floor), classic 0.4/2.6, medium 0.2/3.2, high 0.1/3.5.

**Dashboard gates:** hit rate ≥ 2%; Cross-Mode RTP ≤ **0.50pp**; per-mode
RTP ≤ 0.967; Base Mode STD ≥ **0.60** (leave margin — 0.606 displays as
0.60 and fails). All 40 modes target **0.950**. Treat verifier warnings
as failures.

Wiki: [[codebase/luma-keno]] in `math/wiki/`.

## After `create_books`

1. Overwrite LUT weights with exact `C(20,h)*C(60,k-h)` (uint64).
2. Copy to `lookUpTable_<mode>_0.csv` (publish name).
3. `generate_configs(gamestate)`.
4. From `math/`: `python3 -m utils.rgs_verification -g keno`.
5. Treat verifier **warnings as failures**.

Do not upload `configs/` or web dist. Publish only
`library/publish_files/` (`index.json` + `.jsonl.zst` + LUT `_0.csv`).

## Paytable and ratings

Design order (do not skip): [paytable.md](paytable.md).

1. Fix N=80, K=20, pick range, target RTP, 3-Star caps.
2. For each k, choose which hit counts pay 0.
3. Allocate remaining RTP across paying hits; `m_h = budget_h / P(h)`.
4. Round to 0.1×; recompute exact RTP; iterate.
5. Analytical P5K / P10K / stddev / CVaR / ETL — keno needs **no MC**.
6. If a gate fails: change the table, regenerate. Never clamp.

Binding case is usually **high-variance `pick_10`**. A 10/10 prize near
10,000× is almost never legal: `P(X=10) ≈ 1.12e-4`, so that prize alone
is ~1.12 RTP if paid at 10,000×.

## Commands

From `math/` (Python ≥ 3.12):

```sh
make setup
make run GAME=keno
make run GAME=luma-keno
PYTHONPATH=".:games/luma-keno" python3 -m utils.rgs_verification -g luma-keno
PYTHONPATH=".:games/luma-keno" python3 games/luma-keno/export_luts.py
python3 ../.cursor/skills/keno-math/scripts/rtp.py path/to/paytable.json
```

Debug: `compression=False`, `num_threads=1`. Production compression on.
Sim count is `k+1` per mode (2 books for pick_1), not 100k.

## Do / don't

| Do | Don't |
| --- | --- |
| Exact `math.comb` weights | Rust optimizer / simulated hit rates |
| Mode = pick size (and risk) | One `base` mode for all pick sizes |
| Reconstruct draw on the FE | Trust book numbers as the player's card |
| `finalWin` + auto-close | Tower `auto_close_disabled` session pattern |
| Same LUT RTP every pick size (≤0.50pp dashboard) | Split miss weight (0.6× vs 0.7×) to fake a higher pick_1 RTP |
| Build max prize from P(h) | Start from a 10,000× headline then fit |

## Additional resources

- Exact odds and LUT weights: [hypergeometric.md](hypergeometric.md)
- Event contract + FE reconstruction: [events.md](events.md)
- Paytable + 3-Star checks: [paytable.md](paytable.md)
- SDK file roles / `run_spin` MRO: skill `math-sdk` → `game-files.md`
- Vendor docs map: skill `math-sdk` → `wiki-map.md`
- Publish units / `index.json`: `math/docs/rgs_docs/data_format.md`
- Wallet APIs: `math/docs/rgs_docs/RGS.md`
