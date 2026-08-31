#!/usr/bin/env python3
"""Solve luma-keno Earn paytables (Lumen + extras + Pulse priced into 0.950 RTP).

Off tables in paytables.json["risks"] stay as the certified table-only
0.950 chart. This script writes paytables.json["earn"] so Earn modes
pass the same 3-Star gates after bonuses.

Publish gates (Stake Engine dashboard — binding, stricter than the local
rgs_verification warnings):
  - every mode must award a non-zero win at least 1 in 50 (hit rate >= 2%);
  - per-mode RTP <= 0.967 (3-star volatility limit);
  - Cross-Mode RTP Consistency: max-min RTP <= 0.50pp;
  - Base Mode STD >= 0.60 when cost=1 (leave margin; 0.606 displays as 0.60
    and fails the equality gate).

Caps and the sub-40 consolation are on **settled** payouts (after Lumen
and Pulse) so ETL40 / CVaR stay legal. Advertised tops are
settled_cap / (lumen_boost_for × PULSE_BOOST[risk]). Pulse is ×2 except
medium ×3. Buy chips use BUY_LUMEN_BOOST (10× / 100×) instead of Earn ×2.

Dashboard Expected Tail Liability (Sum) is etl40 + etl10k and
double-counts any win that is both ≥40× cost and ≥10,000× the base bet.
3-Star limit 1.500 (2-Star 1.300). Local `GATES["etl_sum"]` is 1.45.

Structure per (risk, k):
  - consolation tier at the first paying hit: settled sub-40x, fixed RTP share
    (keeps ETL40 under the 0.9 gate) and lifts the hit rate above the
    1-in-50 floor,
  - classic/low only: a fixed 0.5x refund one hit below pay start when
    P(h) <= 0.35 (Stake Originals Low-style "gentle bleed"; 0.5x = 50 LUT
    units, legal on the 0.1x grid). medium/high stay jackpot-shaped,
  - remaining budget water-filled over rarer hits, m_h = c * coeff(h)^-beta,
    capped by a ladder below the risk top (keeps CVaR/std/max-m legal),
  - 0.1x grid convergence: greedy coin fill, then a hill-climb over single
    and paired +/-0.1 moves. Caps and monotonicity are never violated;
    infeasible shapes are reported, never silently clamped.

Writes paytables.json (game) and ../../../web/src/data/keno-paytables.json.
"""

from __future__ import annotations

import json
import math
import os

from keno_pick_one import (
    HIT_WEIGHT,
    MISS_WEIGHT,
    MODE_RTP_BAND,
    PICK_ONE_BONUS_WEIGHT,
    PICK_ONE_MISS,
    PULSE_BOOST,
    RTP_TARGET,
    STD_MIN,
    base_coeff,
    base_stats,
    effective_coeff,
    lumen_boost_for,
    lumen_placed_on_pick,
    pick_one_bonus_miss,
    pick_one_rtp,
    pick_one_row,
    pick_one_row_earn,
    pick_one_std,
    pick_one_std_earn,
    settled_rtp,
    settled_stats,
)
from web_paths import resolve_web_file

POOL = 40
DRAWN = 10
PICKS = range(1, 11)

RTP_TOL = 0.0005  # grid-search convergence tolerance
# MODE_RTP_BAND is imported from keno_pick_one — the pick_1 lattice search needs
# it too, and two copies drift.
# Dashboard Cross-Mode RTP Consistency: <= 0.50pp. Local verifier is 5pp.
SPREAD_MAX = 0.005
# Dashboard: non-zero win at least 1 in 50. Keep margin.
HIT_RATE_MIN = 0.021

RISK_SHAPES = {
    # beta: tail steepness; top: max multiplier on the top hit;
    # sub40: RTP share carried by the sub-40x consolation tier.
    "classic": {"beta": 0.55, "top": 800.0, "sub40": 0.30},
    "low": {"beta": 0.35, "top": 400.0, "sub40": 0.45},
    "medium": {"beta": 0.75, "top": 1500.0, "sub40": 0.22},
    "high": {"beta": 0.90, "top": 4900.0, "sub40": 0.18},
}

# First paying hit per (risk, k). Chosen so every mode clears the 1-in-50
# hit-rate floor: e.g. high pick_8 pays from 4 hits (P(>=4) ~= 8.9%) —
# paying only from 5 gave 1 in 68.8 and failed the dashboard gate.
# Lowest hit count that pays. This is the real dial on dead Lumen: the Lumen
# marks a number whether or not the row pays, so P(dead catch) is just P(hits <
# start). Removing the `base > 0` guard in lumen_pay would do nothing — zero
# times any boost is zero — and a flat rescue floor adds +2.24pp RTP on
# high_pick_10_earn, which there is no ceiling headroom for at 0.965.
#
# Lowered by one on the nine modes where it was affordable, all medium/high:
#   high 6:   4 -> 3    97.4% -> 84.7%
#   high 7:   4 -> 3    94.8% -> 77.2%
#   high 8:   4 -> 3    91.1% -> 68.8%
#   high 9:   5 -> 4    97.1% -> 86.2%
#   high 10:  5 -> 4    95.0% -> 80.3%
#   medium 7: 4 -> 3    94.8% -> 77.2%
#   medium 8: 4 -> 3    91.1% -> 68.8%
#   medium 9: 5 -> 4    97.1% -> 86.2%
#   medium 10:5 -> 4    95.0% -> 80.3%
# It buys hit frequency at the same time, which is why high_pick_6 was worth its
# 50% top-prize cut: it sat at 0.0267 against a 0.02 gate floor and is now at
# 0.1554, so the change removed a certification risk as well as a dead catch.
#
# Two modes are deliberately left alone, because past this point the trade stops
# being worth it and starts dismantling the risk ladder:
#
#   high 4 (95.8%) — the worst remaining. Lowering it to 2 cuts dead to 74.4%
#     but costs 69% of the top prize (613x -> 190x) and takes hit rate from
#     0.0426 to 0.2559. Unlike pick_6 there was no gate pressure to justify it.
#   pick_5, medium and high (91.1%) — lowering to 2 clears the last modes over
#     90%, but takes high_pick_5's hit rate to 0.3669, identical to medium's, so
#     "high risk" would hit better than one round in three, and halves the top
#     prize (798x -> 479x).
#
# pick_8 by contrast was free: medium's top rose 1046x -> 1500x, high's held at
# 4900x. Take the free ones, refuse the ones billed to the mode's identity.
#
# The residual dead catches are a presentation problem, not a math one, and are
# handled there: under the honest preset a dead catch plays the miss cue rather
# than the Lumen cue, so the celebration stops lying even when it still fires.
#
# classic/low are untouched: they are the REFUND_RISKS, so `start` also sets
# `refund_hit = start - 1`, and moving it would silently relocate the push tier.
PAY_START = {
    "classic": {2: 1, 3: 1, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 4},
    "low": {2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4},
    "medium": {2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4},
    "high": {2: 1, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4},
}

# Refund tier: classic/low only. One hit below the pay start pays a fixed
# REFUND_X (1.0x = 100 LUT units — legal: multiple of 10). This mirrors Stake
# Originals Low risk (pays small amounts on low hits: "a gentle bleed");
# medium/high stay jackpot-shaped (Stake High pays nothing until 3-4 hits).
# Guard: only where P(h) <= REFUND_P_MAX — a refund on a likely outcome
# (e.g. classic pick_4 h=1, P=0.44) burns over a fifth of the RTP budget.
# pick_2/pick_3 have no tier below start (h would be 0), so no refund there.
REFUND_RISKS = ("classic", "low")
# 1.0x, was 0.5x. At 0.5x this tier returned half the stake on a losing row: a
# loss dressed as a win, and the single largest contributor to the LDW rate. At
# 1.0x it returns the stake exactly, which is a push — the player is not up, the
# UI has no reason to celebrate, and the round is honestly neutral.
#
# It costs no hit frequency, which is why this is the cheap move: sub-1x rows are
# load-bearing for the 2% win-rate floor (high_pick_6 sits at 0.0267 with little
# headroom), so removing the tier outright was never an option. Doubling its
# price is clawed back from the tail automatically by the water-fill.
REFUND_X = 1.0
REFUND_P_MAX = 0.35


def refund_pay(
    risk: str, cost: float, buy: str | None, earn: bool
) -> float:
    """Fixed refund tier, kept under the dashboard 10k× line after Lumen.

    On buy100, Lumen ×100 would turn a 1.0-of-cost push into exactly 10,000×
    the base bet and double-count it in ETL sum. Stay a tick under.
    """
    if not earn or buy is None:
        return REFUND_X
    boost = lumen_boost_for(risk, buy)
    under = floor_grid(10000.0 / cost / boost - 1e-12, cost)
    return min(REFUND_X, max(grid_step(cost), under))

# Buy chips. Cost is a multiple of the stake; the solved rows are in multiples of
# that cost and scaled up on output, so both ladders share one solve.
BUY_COSTS = {"buy10": 10.0, "buy100": 100.0}


def grid_step(cost: float = 1.0) -> float:
    """One advertised tick in cost units, equal to 0.1× the base bet on export.

    LUT column 3 is a multiple of 10 (0.1× base). A 0.1 step in *cost* units
    makes the smallest buy100 cell 10× base, and BUY_LUMEN_BOOST 100× turns
    that into 1,000× — the coarse grid overshoots target. `0.1 / cost` keeps
    every ladder on the same 0.1×-of-stake lattice Off/Earn already use.
    """
    return round(0.1 / cost, 10)


def _grid_ticks(cost: float) -> float:
    """Ticks per cost-unit. cost=1 → 10 (0.1x); buy100 → 1000 (0.001 of cost)."""
    return 10.0 * cost


def on_grid(x: float, cost: float = 1.0) -> float:
    ticks = _grid_ticks(cost)
    return round(x * ticks) / ticks


def floor_grid(x: float, cost: float = 1.0) -> float:
    ticks = _grid_ticks(cost)
    return math.floor(x * ticks + 1e-9) / ticks

# Cap ladder by distance below the top hit: fraction of risk top, and an
# absolute ceiling so big headline prizes cannot drag mid tiers up.
CAP_FRACTION = [1.0, 0.6, 0.4, 0.3, 0.2]
CAP_ABSOLUTE = [float("inf"), 2500.0, 1500.0, 1000.0, 1000.0]

# Per-pick settled ceiling, overriding the risk top where the top row alone
# drives the dashboard's volatility rating.
#
# A top row contributes p(top) * m^2 to variance. p falls ~15x per pick while the
# ceiling rises, so the product peaks mid-ladder rather than at pick 10: high's
# top row is 94% of variance at pick 6, 56% at pick 7 and 4% at pick 8. That put
# high_pick_6 at std 25.7 against 11-18 for every other pick at that risk, and
# the dashboard rated it Extreme where the rest of the ladder is not.
#
# Capping the ceiling is the whole fix. The paying tiers do not change, so hit
# rate is untouched and the freed RTP redistributes across the mid rows.
TOP_OVERRIDE = {
    # 3,372x -> 2,000x, landing std 16.4 between pick_7 (16.6) and pick_9 (16.1).
    ("high", 6): 2000.0,
}

# Dashboard "Max Payout Multiplier": the largest multiple of the *base bet* the
# game can land, gated at 50,000x for 2-Star and 100,000x for 3-Star (the higher
# tier tolerates more volatility, so it is the looser of the two).
#
# This binds on the buy chips and nothing else. A buy round's rows are scaled by
# its cost on export, so its ceiling is reported against a bet `cost` times
# smaller than the wager: buy100's top row is 4,900x what the player actually
# staked — the same ceiling Earn has — but reads as 490,000x the base bet, and
# failed 15 modes at 2-Star and 9 at 3-Star.
#
# Keyed by cost, in base-bet multiples, each held ~10% under the tier it answers
# to. `rgs_verification` never checked this (max_win was computed and then left
# out of `mode_limits`), which is why it reached the dashboard.
MAX_PAYOUT_ABS = {
    # Off/Earn peak at 4,900x, three orders under either tier. Present so the
    # gate is uniform rather than a buy-only special case.
    1.0: 100_000.0,
    # buy10 reached 49,000 against 2-Star's 50,000 — a 2% margin, against this
    # repo's own rule of designing below the published maxima.
    10.0: 45_000.0,
    # buy100 cannot reach 2-Star at any ceiling worth shipping, so it targets
    # 3-Star's 100,000. Costs high's top row 1,225x -> 225x of cost.
    100.0: 90_000.0,
}

# Local verifier limits (rgs_verification.py) minus margin.
GATES = {
    "p5k": 0.009,
    "p10k": 0.0045,
    "etl40": 0.88,
    "etl10k": 0.70,
    # Dashboard ETL (Sum) = etl40 + etl10k. 3-Star 1.500 / 2-Star 1.300.
    # Leave margin; do not sit on 1.500.
    "etl_sum": 1.45,
    "cvar": 700.0,
    "std": 55.0,
    "std_min": STD_MIN,
    "max_m": 10000.0,
}


def hit_weight(k: int, h: int) -> int:
    rest = POOL - DRAWN
    if h < 0 or h > k or (k - h) > rest or h > DRAWN:
        return 0
    return math.comb(DRAWN, h) * math.comb(rest, k - h)


def probabilities(k: int, placed: bool = False) -> list[float]:
    """P(main hits = h). `placed` conditions on one pick already being in the ten."""
    if placed:
        total = math.comb(POOL - 1, k - 1)
        return [
            (
                math.comb(DRAWN - 1, h - 1) * math.comb(POOL - DRAWN, k - h) / total
                if h >= 1
                else 0.0
            )
            for h in range(k + 1)
        ]
    total = math.comb(POOL, k)
    return [hit_weight(k, h) / total for h in range(k + 1)]


def cap_for(risk: str, k: int, h: int, cost: float = 1.0) -> float:
    """Settled (after Lumen) ceiling for advertised hit h, in units of `cost`.

    The third term is the dashboard's Max Payout Multiplier. It has to be
    divided by `cost` because the ladder is solved in cost units and scaled up
    on export, so a ceiling that looks modest here is `cost` times larger
    against the base bet the gate measures.
    """
    dist = min(k - h, len(CAP_FRACTION) - 1)
    # The absolute limit lowers the risk ceiling the fraction ladder steps down
    # from; it does not clamp each tier independently. Clamping flattens the top
    # tiers onto the same value, and `_fill_from` then has to break the cap to
    # keep payouts strictly increasing — medium buy100 landed on 150.1 against a
    # 150.0 cap that way.
    top = min(
        TOP_OVERRIDE.get((risk, k), RISK_SHAPES[risk]["top"]),
        MAX_PAYOUT_ABS[cost] / cost,
    )
    return min(top * CAP_FRACTION[dist], CAP_ABSOLUTE[dist])


def planned_paying(
    risk: str,
    k: int,
    earn: bool = True,
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
    cost: float = 1.0,
) -> frozenset[int]:
    if k == 1:
        return frozenset({0, 1})
    paying = set(range(PAY_START[risk][k], k + 1))
    rh = refund_hit(risk, k, earn, bought, placed, buy, cost)
    if rh is not None:
        paying.add(rh)
    return frozenset(paying)


def settle_factor(risk: str, earn: bool, buy: str | None = None) -> float:
    """Multiplier between an advertised prize and its settled worst case.

    Earn prices Lumen and Pulse in, so an advertised 10x can settle at 100x on
    High. Buy chips use BUY_LUMEN_BOOST (10× / 100×) instead of the Earn ×2.
    Off has neither channel, so advertised == settled and the caps apply
    directly.
    """
    return lumen_boost_for(risk, buy) * PULSE_BOOST[risk] if earn else 1.0


def pay_coeff(
    risk: str,
    k: int,
    earn: bool = True,
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
    cost: float = 1.0,
) -> list[float]:
    """RTP = sum coeff[h] * advertised[h].

    Earn folds the Lumen and Pulse expectation into the coefficient; Off is
    plain hypergeometric. `bought` is Earn with the extras forced open.
    `placed` is the buy guarantee: marked pick is forced into the ten.
    """
    if not earn:
        return list(base_coeff(k))
    return list(
        effective_coeff(
            risk,
            k,
            planned_paying(risk, k, earn, bought, placed, buy, cost),
            bought,
            placed,
            buy,
        )
    )


def advertised_cap(
    risk: str,
    k: int,
    h: int,
    earn: bool = True,
    cost: float = 1.0,
    buy: str | None = None,
) -> float:
    """Advertised ceiling so the settled prize stays under `cap_for`."""
    return floor_grid(
        cap_for(risk, k, h, cost) / settle_factor(risk, earn, buy), cost
    )


def consolation_cap(
    risk: str, earn: bool = True, buy: str | None = None, cost: float = 1.0
) -> float:
    """Keep settled consolation under 40× so it does not load ETL40."""
    return floor_grid(39.9 / settle_factor(risk, earn, buy), cost)


def mode_stats_for(
    risk: str,
    k: int,
    table: list[float],
    earn: bool,
    bought: bool = False,
    placed: bool = False,
    cost: float = 1.0,
    buy: str | None = None,
) -> dict:
    return (
        settled_stats(risk, k, table, bought, placed, cost=cost, buy=buy)
        if earn
        else base_stats(k, table)
    )


def tail_capacity_of(p: list[float], tail: list[int], caps: dict) -> float:
    return sum(p[h] * caps[h] for h in tail)


def _table_valid(
    m: list[float], start: int, k: int, caps: dict, cost: float = 1.0
) -> bool:
    step = grid_step(cost)
    if any(m[h] < step - 1e-9 for h in range(start, k + 1)):
        return False
    if any(m[h] > caps[h] + 1e-9 for h in range(start, k + 1)):
        return False
    # m[start - 1] is the fixed refund tier (if any); it must not exceed start.
    if start >= 1 and m[start - 1] > 0 and m[start] < m[start - 1] - 1e-9:
        return False
    return all(m[h + 1] >= m[h] - 1e-9 for h in range(start, k))


def _grid_moves(
    m: list[float], start: int, k: int, caps: dict, cost: float = 1.0
):
    """Single +/-step moves that keep floors, caps and monotonicity."""
    step = grid_step(cost)
    for h in range(start, k + 1):
        floor = (
            m[start - 1] + step
            if h == start and start >= 1 and m[start - 1] > 0
            else (step if h == start else m[h - 1] + step)
        )
        ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - step)
        for d in (step, -step):
            if floor - 1e-9 <= m[h] + d <= ceiling + 1e-9:
                yield h, d


def _refine(
    m: list[float],
    p: list[float],
    start: int,
    k: int,
    caps: dict,
    cost: float = 1.0,
) -> float:
    """Hill-climb |RTP - target| over single and paired grid moves."""
    step = grid_step(cost)

    def err_of(table: list[float]) -> float:
        return sum(pi * mi for pi, mi in zip(p, table)) - RTP_TARGET

    best_err = err_of(m)
    for _ in range(5000):
        if abs(best_err) <= RTP_TOL:
            break
        improved = False
        for h, d in _grid_moves(m, start, k, caps, cost):
            new_err = best_err + d * p[h]
            if abs(new_err) < abs(best_err) - 1e-12:
                m[h] = round(m[h] + d, 10)
                best_err = new_err
                improved = True
        if improved:
            continue
        # No single move helps: try pairs (+step on one tier, -step on another).
        pair = None
        for h1, d1 in _grid_moves(m, start, k, caps, cost):
            if abs(d1 - step) > 1e-12:
                continue
            for h2, d2 in _grid_moves(m, start, k, caps, cost):
                if abs(d2 + step) > 1e-12 or h2 == h1:
                    continue
                cand = list(m)
                cand[h1] = round(cand[h1] + step, 10)
                cand[h2] = round(cand[h2] - step, 10)
                if not _table_valid(cand, start, k, caps, cost):
                    continue
                cand_err = err_of(cand)
                if abs(cand_err) < abs(best_err) - 1e-12 and (
                    pair is None or abs(cand_err) < abs(pair[0])
                ):
                    pair = (cand_err, cand)
        if pair is None:
            break
        best_err, m[:] = pair[0], pair[1]
    return abs(best_err)


def refund_hit(
    risk: str,
    k: int,
    earn: bool = True,
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
    cost: float = 1.0,
) -> int | None:
    """Hit count that pays the fixed REFUND_X, or None when not applicable.

    One below the pay start, classic/low only, pick_2/pick_3 excluded (they pay
    from 1 hit, so there is no tier below start to refund), and subject to two
    affordability tests:

    - `P(h) <= REFUND_P_MAX`, a shape guard: a refund on a *likely* outcome
      (classic pick_4 h=1, P=0.44) is a consolation tier wearing a refund's
      clothes.
    - the budget test below, which is what actually binds since REFUND_X went to
      1.0. Paying the tier forces `start >= REFUND_X + 0.1`, and monotonicity on
      a 0.1x grid then forces the whole ladder above it up: 1.1, 1.2, 1.3, ...
      Pricing only the refund plus the start tier is not enough — on
      low_pick_8_earn that pair costs 0.75 and looks affordable, while the full
      forced ladder costs 0.9933 against a 0.965 target. The mode is infeasible
      with the tier, and without this test the solver silently returns that
      0.9933 as a convergence failure instead of dropping the tier.
    """
    if risk not in REFUND_RISKS:
        return None
    h = PAY_START[risk][k] - 1
    if h < 1:
        return None
    if probabilities(k, placed)[h] > REFUND_P_MAX:
        return None
    start = PAY_START[risk][k]
    # Coefficients computed here rather than via pay_coeff: for earn that routes
    # through planned_paying, which calls back into this function. The paying set
    # is the one this test is about — the tier present — so building it inline is
    # both cycle-free and the right scenario to price.
    if earn:
        paying = frozenset(set(range(start, k + 1)) | {h})
        p = list(effective_coeff(risk, k, paying, bought, placed, buy))
    else:
        p = list(base_coeff(k))
    # Cheapest table that still honours the refund tier and monotone grid steps.
    rx = refund_pay(risk, cost, buy, earn)
    step = grid_step(cost)
    min_rtp = p[h] * rx + sum(
        p[t] * (rx + step * (t - start + 1)) for t in range(start, k + 1)
    )
    if min_rtp > RTP_TARGET:
        return None
    return h


def _fill_from(
    risk: str,
    k: int,
    start_pay: float | None,
    earn: bool = True,
    bought: bool = False,
    cost: float = 1.0,
    placed: bool = False,
    cap_overrides: dict[int, float] | None = None,
    buy: str | None = None,
) -> list[float]:
    """Water-fill + grid-converge with a fixed (or designed) consolation pay."""
    p = pay_coeff(risk, k, earn, bought, placed, buy, cost)
    beta = RISK_SHAPES[risk]["beta"]
    start = PAY_START[risk][k]
    caps = {h: advertised_cap(risk, k, h, earn, cost, buy) for h in range(start, k + 1)}
    if cap_overrides:
        caps = {h: min(v, cap_overrides[h]) if h in cap_overrides else v for h, v in caps.items()}
    tail = [h for h in range(start + 1, k + 1)]
    rh = refund_hit(risk, k, earn, bought, placed, buy, cost)
    rx = refund_pay(risk, cost, buy, earn)
    refund_cost = p[rh] * rx if rh is not None else 0.0
    step = grid_step(cost)
    # With a refund tier below start, keep monotonicity: start >= refund + step.
    min_start = rx + step if rh is not None else step
    sub40 = consolation_cap(risk, earn, buy, cost)
    caps = {h: max(v, min_start) if h == start else v for h, v in caps.items()}

    sub40_budget = min(RISK_SHAPES[risk]["sub40"] * RTP_TARGET, p[start] * min(sub40, caps[start]))
    if start_pay is None:
        m_start = max(min_start, on_grid(sub40_budget / p[start], cost))
        m_start = min(m_start, sub40, caps[start])
    else:
        m_start = min(max(min_start, on_grid(start_pay, cost)), sub40, caps[start])
    # Never let the consolation alone overshoot the target: remaining budget
    # must stay >= 0 so the tail fill is well-defined. The refund tier below
    # start is fixed and spends its budget first.
    m_start = min(
        m_start,
        math.floor((RTP_TARGET - refund_cost) / p[start] * _grid_ticks(cost) - 1e-9)
        / _grid_ticks(cost),
    )

    m = [0.0] * (k + 1)
    if rh is not None:
        m[rh] = rx
    m[start] = m_start
    remaining = RTP_TARGET - p[start] * m[start] - refund_cost

    if tail:
        def total_for(c: float) -> float:
            return sum(p[h] * min(c * p[h] ** -beta, caps[h]) for h in tail)

        # When an etl_sum retry has lowered the top cap, the tail may not be
        # able to absorb `remaining`. Bound the search so we fill to cap
        # instead of doubling `hi` forever.
        tail_cap_rtp = sum(p[h] * caps[h] for h in tail)
        fill_remaining = min(remaining, tail_cap_rtp)
        lo, hi = 0.0, 1.0
        if fill_remaining > 0:
            while total_for(hi) < fill_remaining and hi < 1e18:
                hi *= 2.0
            for _ in range(100):
                mid = (lo + hi) / 2
                if total_for(mid) < fill_remaining:
                    lo = mid
                else:
                    hi = mid
            c = (lo + hi) / 2
        else:
            c = 0.0
        for h in tail:
            m[h] = round(min(c * p[h] ** -beta, caps[h]) * _grid_ticks(cost)) / _grid_ticks(cost)
            # Keep payouts non-decreasing across hits even when the shape
            # wants a dip right above the consolation tier.
            m[h] = max(m[h], round(m[h - 1] * _grid_ticks(cost) + 1) / _grid_ticks(cost))

    # Grid rounding: floor every tier to the step, then buy the leftover back
    # with step-sized coins (largest coin that fits, smallest overshoot otherwise).
    def rtp() -> float:
        return sum(pi * mi for pi, mi in zip(p, m))

    for h in range(start, k + 1):
        if m[h] > 0:
            m[h] = floor_grid(m[h], cost)
            m[h] = max(min_start if h == start else step, m[h])

    for _ in range(max(2000, int(round(200 / step)))):
        leftover = RTP_TARGET - rtp()
        if abs(leftover) <= RTP_TOL:
            break
        if leftover < 0:
            best = None
            for h in range(start, k + 1):
                floor_h = min_start if h == start else m[h - 1] + step
                if m[h] - step < floor_h - 1e-9:
                    continue
                coin = p[h] * step
                if best is None or coin < best[0]:
                    best = (coin, h)
            if best is None:
                break
            m[best[1]] = round(m[best[1]] - step, 10)
            continue
        best = None  # (coin, h)
        for h in range(start, k + 1):
            coin = p[h] * step
            ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - step)
            if m[h] + step > ceiling + 1e-9:
                continue
            if coin <= leftover + 1e-12 and (best is None or coin > best[0]):
                best = (coin, h)
        if best is None:
            for h in range(start, k + 1):
                coin = p[h] * step
                ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - step)
                if m[h] + step > ceiling + 1e-9:
                    continue
                if best is None or coin < best[0]:
                    best = (coin, h)
        if best is None:
            break
        m[best[1]] = round(m[best[1]] + step, 10)

    _refine(m, p, start, k, caps, cost)
    return m


def solve_table(
    risk: str,
    k: int,
    earn: bool = True,
    bought: bool = False,
    cost: float = 1.0,
    placed: bool = False,
    buy: str | None = None,
) -> tuple[list[float], list[str]]:
    errors: list[str] = []
    p = pay_coeff(risk, k, earn, bought, placed, buy, cost)
    start = PAY_START[risk][k]
    caps = {h: advertised_cap(risk, k, h, earn, cost, buy) for h in range(start, k + 1)}
    tail = [h for h in range(start + 1, k + 1)]
    rh = refund_hit(risk, k, earn, bought, placed, buy, cost)
    rx = refund_pay(risk, cost, buy, earn)
    refund_cost = p[rh] * rx if rh is not None else 0.0
    step = grid_step(cost)
    min_start = rx + step if rh is not None else step
    sub40 = consolation_cap(risk, earn, buy, cost)

    # Consolation tier: settled sub-40x, fixed RTP share. The cap ladder and the
    # water-fill shape already leave the tail below target on its own, so the
    # consolation share is used as-is unless caps make it impossible.
    sub40_budget = RISK_SHAPES[risk]["sub40"] * RTP_TARGET
    max_consolation = p[start] * min(sub40, caps[start])
    if tail_capacity_of(p, tail, caps) + max_consolation + refund_cost < RTP_TARGET:
        errors.append("budget infeasible: caps cannot reach target RTP")
        return [0.0] * (k + 1), errors
    sub40_budget = min(sub40_budget, max_consolation)
    if sub40_budget < RISK_SHAPES[risk]["sub40"] * RTP_TARGET * 0.5:
        errors.append(
            f"consolation tier too small: {sub40_budget:.3f} of "
            f"{RISK_SHAPES[risk]['sub40'] * RTP_TARGET:.3f}"
        )

    def err_of(table: list[float]) -> float:
        return sum(pi * mi for pi, mi in zip(p, table)) - RTP_TARGET

    def fill_best(overrides: dict[int, float] | None) -> tuple[list[float], float, dict[int, float]]:
        use = {h: advertised_cap(risk, k, h, earn, cost, buy) for h in range(start, k + 1)}
        if overrides:
            use = {h: min(v, overrides[h]) if h in overrides else v for h, v in use.items()}
        designed = _fill_from(
            risk, k, None, earn, bought, cost, placed, cap_overrides=overrides, buy=buy
        )
        best = (abs(err_of(designed)), designed)
        if best[0] > RTP_TOL * 2:
            lo_pay = min_start
            hi_pay = min(
                sub40,
                use[start],
                max(2.0 / cost, on_grid(sub40_budget / p[start] * 2, cost)),
            )
            steps = int(round((hi_pay - lo_pay) / step)) + 1
            # Fine buy grids would scan thousands of start pays. Cap the
            # consolation search; the designed fill already sits on the step.
            if steps > 40:
                scan = on_grid((hi_pay - lo_pay) / 39, cost) or step
                steps = int(round((hi_pay - lo_pay) / scan)) + 1
            else:
                scan = step
            for i in range(steps):
                cand_pay = round(lo_pay + scan * i, 10)
                cand = _fill_from(
                    risk,
                    k,
                    cand_pay,
                    earn,
                    bought,
                    cost,
                    placed,
                    cap_overrides=overrides,
                    buy=buy,
                )
                if not _table_valid(cand, start, k, use, cost):
                    continue
                cand_err = abs(err_of(cand))
                if cand_err < best[0] - 1e-9 or (
                    abs(cand_err - best[0]) <= 1e-9 and cand[start] > best[1][start]
                ):
                    best = (cand_err, cand)
        return best[1], best[0], use

    # The designed fill can strand the RTP on the wrong side of a lattice
    # gap (e.g. pick_2: [0, 0.5, 13.1] = 0.9481 while [0, 0.1, 15.8] is
    # exactly 0.95). When it misses tolerance, scan the consolation pay
    # over the 0.1x grid and keep the variant landing closest to target;
    # ties prefer the larger consolation (better hit-rate feel).
    m, residual, caps = fill_best(None)
    if residual > RTP_TOL * 4:
        errors.append(f"grid convergence residual {residual:.5f}")

    # Dashboard ETL (Sum) double-counts a top that is both ≥40× cost and
    # ≥10,000× the base bet. Guaranteed catch puts the chip boost on every
    # paying row, so a full card is always ×10 / ×100 and mid hits carry it
    # too. Shrink the advertised top (first to just under the 10k/Lumen line,
    # then 15% steps) and refill so leftover RTP lands on more frequent mid
    # hits. Fail closed if the refill cannot reach target — do not clamp.
    stats = mode_stats_for(risk, k, m, earn, bought, placed, cost, buy)
    overrides: dict[int, float] = {}
    boost = lumen_boost_for(risk, buy) if earn else 1.0
    under_10k = floor_grid(10000.0 / cost / boost - 1e-12, cost)
    for _ in range(12):
        if stats["etl_sum"] <= GATES["etl_sum"]:
            break
        floor_top = (m[k - 1] + step) if k > start else min_start
        if m[k] > under_10k + 1e-9:
            new_top = under_10k
        else:
            new_top = floor_grid(m[k] * 0.85, cost)
        if new_top < floor_top - 1e-9:
            break
        trial = dict(caps)
        trial[k] = new_top
        if (
            tail_capacity_of(p, tail, trial) + max_consolation + refund_cost
            < RTP_TARGET
        ):
            break
        overrides[k] = new_top
        m, residual, caps = fill_best(overrides)
        if residual > RTP_TOL * 4:
            errors.append(f"grid convergence residual {residual:.5f} after etl_sum shrink")
            break
        stats = mode_stats_for(risk, k, m, earn, bought, placed, cost, buy)

    if not _table_valid(m, start, k, caps, cost):
        errors.append("cap or monotonicity violated after grid search")
    return m, errors


def mode_stats(risk: str, k: int, table: list[float]) -> dict:
    return settled_stats(risk, k, table)


def check_gates(
    k: int, stats: dict, *, earn: bool = False, cost: float = 1.0
) -> list[str]:
    f: list[str] = []
    lo, hi = MODE_RTP_BAND
    if not (lo <= stats["rtp"] <= hi):
        f.append(f"rtp={stats['rtp']:.4f} outside {lo:.4f}-{hi:.4f}")
    # Off pick_1 has a closed form, so it must land on target exactly rather
    # than merely inside the band.
    if k == 1 and not earn and abs(stats["rtp"] - RTP_TARGET) > 1e-9:
        f.append(
            f"advertised rtp={stats['rtp']:.4f} != {RTP_TARGET:.4f} lattice"
        )
    if stats["hit_rate"] < HIT_RATE_MIN:
        f.append(f"hit_rate={stats['hit_rate']:.4f} < {HIT_RATE_MIN:.4f} (1 in {1 / stats['hit_rate']:.1f})")
    if stats["p5k"] > GATES["p5k"]:
        f.append(f"p5k={stats['p5k']:.1e}")
    if stats["p10k"] > GATES["p10k"]:
        f.append(f"p10k={stats['p10k']:.1e}")
    if stats["etl40"] > GATES["etl40"]:
        f.append(f"etl40={stats['etl40']:.3f}")
    if stats["etl10k"] > GATES["etl10k"]:
        f.append(f"etl10k={stats['etl10k']:.3f}")
    if stats["etl_sum"] > GATES["etl_sum"]:
        f.append(f"etl_sum={stats['etl_sum']:.3f}")
    if stats["cvar"] > GATES["cvar"]:
        f.append(f"cvar={stats['cvar']:.0f}")
    if stats["std"] > GATES["std"]:
        f.append(f"std={stats['std']:.1f}")
    # Dashboard Base Mode STD is the cost=1 envelope. Buy chips are
    # is_buybonus with cost 10/100; the floor does not apply to them.
    if cost == 1.0 and stats["std"] < GATES["std_min"]:
        f.append(f"std={stats['std']:.3f} < {GATES['std_min']} (Base Mode STD floor)")
    if stats["max_m"] > GATES["max_m"]:
        f.append(f"max_m={stats['max_m']:.0f}")
    # The same ceiling in the units the dashboard reads: cost units scaled up by
    # `cost`. `max_m` above is per-cost and cannot catch a buy chip whose rows
    # are multiplied by 100 on export.
    if stats["max_m"] * cost > MAX_PAYOUT_ABS[cost]:
        f.append(
            f"max payout {stats['max_m'] * cost:.0f}x base bet > "
            f"{MAX_PAYOUT_ABS[cost]:.0f} (dashboard Max Payout Multiplier)"
        )
    # k >= 2 needs at least two paying tiers.
    if len(stats["nonzero_payouts"]) < 2:
        f.append("fewer than 2 nonzero payouts")
    return f


def buy_pick_one_row(
    risk: str, cost: float = 1.0, buy: str | None = None
) -> tuple[list[float], list[str]]:
    """pick_1 for the buy ladder, solved on the grid rather than in closed form.

    The Off/Earn closed forms assume the only outcomes are miss and hit. Bought
    extras break that: with one pick and no main hit there are still two extra
    numbers that can land, so a miss is reachable from a paying row and the
    two-outcome lattice no longer describes the mode. Two free values on a 0.1x
    grid is a small enough space to search directly.

    pick_1 does not place Lumen (forcing the only pick in collapses variance
    below the STD floor). It still uses BUY_LUMEN_BOOST at the Earn catch rate.
    """
    paying = frozenset({0, 1})
    p = effective_coeff(risk, 1, paying, True, False, buy)
    cap = advertised_cap(risk, 1, 1, True, cost, buy)
    step = grid_step(cost)
    lo, hi = MODE_RTP_BAND
    best: tuple[float, list[float]] | None = None
    n = int(round(cap / step)) + 1
    for miss_i in range(0, n):
        miss = round(miss_i * step, 10)
        if p[0] * miss > hi:
            break
        hit_guess = on_grid((RTP_TARGET - p[0] * miss) / p[1], cost)
        for delta in range(-40, 41):
            hit = round(hit_guess + delta * step, 10)
            if hit <= miss or hit > cap or hit < step:
                continue
            table = [miss, hit]
            rtp = settled_rtp(risk, 1, table, True, False, buy, cost)
            if not lo <= rtp <= hi:
                continue
            err = abs(rtp - RTP_TARGET)
            if best is None or err < best[0] - 1e-12:
                best = (err, table)
    if best is None:
        return [0.0, 0.0], ["pick_1 buy: no grid solution"]
    errors = [] if best[0] <= RTP_TOL * 4 else [
        f"pick_1 buy residual {best[0]:.5f}"
    ]
    return best[1], errors


def _solve_ladder(
    earn: bool,
    bought: bool = False,
    suffix: str = "",
    cost: float = 1.0,
    buy: str | None = None,
) -> tuple[dict[str, dict[str, list[float]]], list[float]]:
    """Solve all 40 tables of one ladder. Off and Earn differ only in the
    coefficient vector, the cap divisor, and the pick_1 closed form."""
    label = suffix.lstrip("_") or ("earn" if earn else "off")
    risks: dict[str, dict[str, list[float]]] = {}
    all_rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for risk in ("classic", "low", "medium", "high"):
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            base_name = f"{risk}_pick_{k}"
            name = f"{base_name}{suffix}" if suffix else (
                f"{base_name}_earn" if earn else base_name
            )
            placed = lumen_placed_on_pick(buy, k)
            if k == 1:
                if bought:
                    table, errors = buy_pick_one_row(risk, cost, buy)
                else:
                    table = pick_one_row_earn(risk) if earn else pick_one_row(risk)
                    errors = []
            else:
                table, errors = solve_table(
                    risk, k, earn, bought, cost, placed, buy
                )
            stats = mode_stats_for(risk, k, table, earn, bought, placed, cost, buy)
            fails = errors + check_gates(k, stats, earn=earn, cost=cost)
            if k == 1 and not bought:
                std = pick_one_std_earn(risk) if earn else pick_one_std(risk)
                if std < STD_MIN:
                    fails.append(f"pick_1 std={std:.3f} < {STD_MIN}")
            if fails:
                failures[name] = fails
            tables[str(k)] = table
            all_rtps.append(stats["rtp"])
            print(
                f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
                f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
                f"etl40={stats['etl40']:.3f} etl_sum={stats['etl_sum']:.3f} "
                f"cvar={stats['cvar']:6.1f} "
                f"p5k={stats['p5k']:.1e} p10k={stats['p10k']:.1e} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':20s} {table}")
        risks[risk] = tables
    if failures:
        raise SystemExit(f"{label} gate failures: {failures}")
    return risks, all_rtps


def solve_off() -> tuple[dict[str, dict[str, list[float]]], list[float]]:
    """Solve the 40 table-only Off modes.

    These used to be passed through from the previous `paytables.json`, which
    silently pinned them to whatever target was in force when they were last
    written. Retargeting Earn alone would have opened a spread the Cross-Mode
    gate rejects, so both ladders are solved together now.
    """
    return _solve_ladder(earn=False)


def solve_earn() -> tuple[dict[str, dict[str, list[float]]], list[float]]:
    """Solve the 40 Earn modes: extras, Lumen, and Pulse priced into target."""
    return _solve_ladder(earn=True)


def solve_buy() -> tuple[dict[str, dict[str, dict[str, list[float]]]], list[float]]:
    """Solve the buy ladders, which used to be carried forward uncertified.

    A buy round is an Earn round with the two extras forced open — that is what
    the purchase buys. Both chips also place the Lumen mark on one of the picks
    (picks 2–10; pick_1 cannot carry the guarantee on the 0.1x lattice). Lumen
    then pays BUY_LUMEN_BOOST (10× / 100×) instead of the Earn ×2; Pulse stays
    at the risk rate. The advertised rows come out in multiples of the *cost*,
    then get scaled to base-stake units on the way out. The 10× / 100× is
    priced into the coefficients, so stacking it on the old Earn-rate tables
    would explode RTP.

    Why that scaling matters. An earlier carried set denominated rows in base
    stake while the round cost 10x or 100x it, so the only thing making a buy
    round worth its price was `lumenBoost = cost` with no re-solve. That put
    90-99% of the return in the Lumen channel. Solving in cost units with the
    chip boost in the coefficients makes the base table carry the round again.

    The verifier normalizes every moment by `bet_cost`, so solving in cost units
    means the gates read exactly as they do for a 1x mode.

    One solve per cost, not one solve scaled twice. The two ladders used to be
    the same cost-unit table multiplied by 10 and 100, which is only valid while
    every gate is per-cost. `MAX_PAYOUT_ABS` is not: it is measured against the
    base bet, so the two chips have genuinely different ceilings in cost units
    (buy10 4,500 / boosts, buy100 900 / boosts) and cannot share a table.
    """
    ladders: dict[str, dict[str, dict[str, list[float]]]] = {}
    rtps: list[float] = []
    for key, cost in BUY_COSTS.items():
        tables, ladder_rtps = _solve_ladder(
            earn=True, bought=True, suffix=f"_{key}", cost=cost, buy=key
        )
        ladders[key] = {
            risk: {
                k: [round(m * cost, 1) for m in row]
                for k, row in rows.items()
            }
            for risk, rows in tables.items()
        }
        rtps.extend(ladder_rtps)
    return ladders, rtps


def check_spread(rtps: list[float]) -> None:
    """Cross-Mode RTP Consistency runs across **all** published modes, not per
    ladder — so it has to be checked on the union."""
    spread = max(rtps) - min(rtps)
    print(
        f"\ncross-mode RTP spread={spread:.4f} over {len(rtps)} modes "
        f"({min(rtps):.4f}-{max(rtps):.4f}); dashboard limit {SPREAD_MAX}"
    )
    if spread > SPREAD_MAX:
        raise SystemExit(f"cross-mode spread {spread:.4f} > {SPREAD_MAX}")


DEFAULT_WALLET = {
    "currency": "USD",
    "unitsPerCredit": 1000000,
    "minBet": 100000,
    "maxBet": 100000000,
    "stepBet": 100000,
    "betLevels": [
        100000, 500000, 1000000, 2500000, 5000000,
        10000000, 25000000, 50000000, 100000000,
    ],
    "defaultBetLevel": 1000000,
}

# Written by this solver. Anything else the client ships (a hand-tuned wallet) is
# carried forward rather than clobbered. buy10/buy100 joined this set when
# `solve_buy` replaced the carried uncertified tables.
SOLVED_KEYS = frozenset(
    {
        "pool",
        "drawn",
        "rtp_target",
        "picks",
        "risks",
        "earn",
        "pick1Bonus",
        "solved",
        *BUY_COSTS,
    }
)


def write_outputs(off: dict, earn: dict, buys: dict) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    payload = {
        "pool": POOL,
        "drawn": DRAWN,
        "rtp_target": RTP_TARGET,
        "picks": {"min": 1, "max": 10},
        "risks": off,
        "earn": earn,
        # Off pick_1's third tier. Both miss amounts are advertised, so the
        # client needs the bonus pay and its odds, not just the row above.
        "pick1Bonus": {
            "weight": PICK_ONE_BONUS_WEIGHT,
            "missWeight": MISS_WEIGHT,
            "total": MISS_WEIGHT + HIT_WEIGHT,
            "pay": {risk: pick_one_bonus_miss(risk) for risk in PICK_ONE_MISS},
        },
        # Which table sections this solve owns. A section can be present in the
        # file without being certified — the buy chips were carried here for
        # months — so consumers cannot infer ownership from presence. Naming it
        # lets the client PAR sheet mark carried sections uncertified instead of
        # crediting them with a solve they never had.
        "solved": ["risks", "earn", *sorted(buys)],
        **buys,
    }
    game_path = os.path.join(here, "paytables.json")
    with open(game_path, "w", encoding="UTF-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(f"wrote {game_path}")

    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    existing: dict = {}
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            existing = json.load(handle)

    # Carried sections first, wallet last — matches the client's existing key
    # order so a no-op solve produces an empty diff.
    web_payload = dict(payload)
    carried = sorted(k for k in existing if k not in SOLVED_KEYS and k != "wallet")
    for key in carried:
        web_payload[key] = existing[key]
    web_payload["wallet"] = existing.get("wallet", DEFAULT_WALLET)

    with open(web_path, "w", encoding="UTF-8") as handle:
        json.dump(web_payload, handle, indent=2)
        handle.write("\n")
    print(f"wrote {web_path}")
    if carried:
        print(
            f"WARNING: carried {len(carried)} unsolved paytable section(s): "
            f"{', '.join(carried)}\n"
            f"  They stay at the old RTP target while risks/earn move to "
            f"{RTP_TARGET:.4f}.\n"
            "  Either add them to the solver or remove them from the client."
        )


if __name__ == "__main__":
    off, off_rtps = solve_off()
    earn, earn_rtps = solve_earn()
    buys, buy_rtps = solve_buy()
    # Buy RTP is per cost, so it belongs in the same spread check as the rest:
    # a player choosing between Earn and a buy chip is choosing between returns
    # on the money they are about to spend either way.
    check_spread(off_rtps + earn_rtps + buy_rtps)
    write_outputs(off, earn, buys)
