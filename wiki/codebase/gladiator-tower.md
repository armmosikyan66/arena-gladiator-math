---
type: codebase
tags: [gladiator-tower, session, publish, rating]
updated: 2026-08-24
---

# Gladiator Tower math

BitKong-style climb in `math/games/gladiator-tower/`. `win_type = "other"` —
not lines/ways/cluster. Rules in `readme.txt`.

## Session vs settle

- **Open** (`easy` / `medium` / `hard` / `extreme` / `nightmare`): book is
  `sessionStart` + `mineLayout` (+ pre-resolved `rowBonuses`). Root
  `payoutMultiplier` = 100 (1×). `auto_close_disabled` so the round stays
  active. UI payout = bet.
- **Settle after close**: `{diff}_loss`, `{diff}_{n}` (ladder depth),
  `{diff}_p{payout×100}` (ladder × bonus product).

Flow: `/wallet/play` open → picks via `/bet/event` → `/wallet/end-round` →
second play of the settle mode → `/wallet/end-round`. Mine: settle `*_loss`
(stake stays lost). Cancel: end-round only on the 1× session book.

## Where logic lives

- Ladder / bonuses / RTP: `game_calculations.py` (`BASE_HOUSE_EDGE=0.01`,
  `EDGE_GROWTH=0.002`, floor to 0.1×).
- Session engine: `session.py` (`start_session`, `pick_tile`, `cash_out`).
- Events: `game_events.py` (`sessionStart`, `tileReveal`).
- Web must **not** roll mines or bonuses; it applies `session.rowBonuses`.

## Rating envelope

New math must satisfy [[domain/stake-rating-limits]] (default **3-Star**)
and be constructed per [[concepts/tower-math-from-ratings]].

> ⚠️ Contradicts [[concepts/tower-math-from-ratings]]: the live ladder is
> still fair-odds × depth house edge, not survival P_k → RTP budget.
> Treat published multipliers as legacy until regenerated. Do not add rows
> or bonuses that push P5K / P10K / CVaR / ETL / max payout past the
> intersection of the brief and `utils/rgs_verification.py`
> ([[analyses/rating-limit-contradictions]]).

## Publish

`run.py`: `create_books` → `generate_configs` → export
`library/configs/math_config.json` (and sync
`web/src/data/tower-math-config.json`) → refresh optimized LUTs from base →
verify `library/publish_files/`.

Constant single-payout LUTs fail Stake stats (`ERR_MATH_OUTSIDE_RANGE`).
Books apply ~±0.1× jitter so each mode has ≥3 distinct payouts.

Run:

```sh
cd math && PYTHONPATH=".:games/gladiator-tower" python3 games/gladiator-tower/run.py
```

Upload the entire `library/publish_files/` directory.

## Related

- [[domain/stake-engine-publish]]
- [[domain/stake-rating-limits]]
- [[concepts/tower-math-from-ratings]]
- [[codebase/sdk-layout]]
- Client gaps: `web/wiki/analyses/stake-engine-compat.md` (math side is this
  package)
