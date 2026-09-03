#!/usr/bin/env python3
"""Solve luma-keno Earn paytables (Lumen + extras + Pulse priced into 0.950 RTP).

Off tables in paytables.json["risks"] stay as the certified table-only
chart, with designed HUD-copy exceptions: Off `low` (Easy leftover-share,
easy_off_low.py), Off `classic` / `medium` / `high` (max-anchored geometric,
easy_off_classic.py / easy_off_medium.py / easy_off_high.py). This script
writes paytables.json["earn"] (and the Off charts) so every mode passes the
same 3-Star gates.

Publish gates (Stake Engine dashboard — binding, stricter than the local
rgs_verification warnings):
  - every mode must award a non-zero win at least 1 in 50 (hit rate >= 2%);
  - per-mode RTP <= 0.967 (3-star volatility limit);
  - Cross-Mode RTP Consistency: max-min RTP <= 0.50pp;
  - Base Mode STD >= 0.60 when cost=1 (leave margin; 0.606 displays as 0.60
    and fails the equality gate).

Caps and the sub-40 consolation are on **settled** payouts (after Lumen
and Pulse) so ETL40 / CVaR stay legal. Advertised tops are
settled_cap / (lumen_boost_for × PULSE_BOOST[risk]). Pulse is ×2 on every
risk. Buy chips use BUY_LUMEN_BOOST (10× / 100×) instead of Earn ×2.

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
    PICK_ONE_BASE_RTP,
    PICK_ONE_BONUS_RISKS,
    PICK_ONE_BONUS_WEIGHT,
    PICK_ONE_MISS,
    PULSE_BOOST,
    RTP_TARGET,
    STD_MIN,
    base_coeff,
    base_stats,
    effective_coeff,
    has_pick_one_bonus,
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
    spin_outcomes,
)
from easy_off_low import EASY_OFF_LOW
from easy_earn_low import EASY_EARN_LOW, MAX_LADDER as EARN_LOW_MAX
from easy_buy_low import EASY_BUY_LOW, EASY_BUY_LOW_PICK1, JSON_MAX_LADDER, cost_row_for as easy_buy_cost_row
from easy_buy_classic import (
    EASY_BUY_CLASSIC,
    EASY_BUY_CLASSIC_BUY100,
    EASY_BUY_CLASSIC_PICK1,
    JSON_MAX_LADDER as CLASSIC_BUY_JSON_MAX_LADDER,
    cost_row_for as easy_buy_classic_cost_row,
    json_max_for as classic_buy_json_max_for,
)
from easy_buy_medium import (
    EASY_BUY_MEDIUM,
    EASY_BUY_MEDIUM_BUY100,
    EASY_BUY_MEDIUM_PICK1,
    JSON_MAX_LADDER as MEDIUM_BUY_JSON_MAX_LADDER,
    cost_row_for as easy_buy_medium_cost_row,
    json_max_for as medium_buy_json_max_for,
)
from easy_buy_high import (
    EASY_BUY_HIGH,
    EASY_BUY_HIGH_BUY100,
    EASY_BUY_HIGH_PICK1,
    JSON_MAX_LADDER as HIGH_BUY_JSON_MAX_LADDER,
    cost_row_for as easy_buy_high_cost_row,
    json_max_for as high_buy_json_max_for,
)
from easy_off_classic import CLASSIC_OFF
from easy_off_medium import MEDIUM_OFF
from easy_off_high import HIGH_OFF
from restaired_rows import scaled_row_for

# Earn `low` Easy analogue. Designed chart is easy_earn_low.py (HUD zeros +
# leftover-share on Earn coefficients). Advertised top is at least the Off
# max so How-to cannot land below Off; picks 8-10 advertise 100x so a full
# card settles 400x. JACKPOT_TOP's 20,000x settled pin must not steal Easy.
EASY_EARN_LOW_TOP = {k: EARN_LOW_MAX[k] for k in range(3, 11)}

# Earn `classic` HUD analogue. Off classic maxes 5.4..1000. Picks 3-5 and 7
# pin at that pick's Off max; pick 6 advertised 80x so 5-of-6 is not a 20x
# cliff. Picks 8-10 copy Off's climb (750 < 900 < 1000) so How-to settles
# 3000 / 3600 / 4000. JACKPOT_TOP must not steal the Classic ceiling.
# 2026-09-01: Off picks 3-6 cut 40/100/300/500 → 17.5/30/75/200.
CLASSIC_EARN_TOP = {
    3: 17.5,   # Off 17.5
    4: 30.0,   # Off 30
    5: 75.0,   # Off 75
    6: 80.0,    # Off 200. 200 left 9.9 -> 200 (20x). 50 How-to-floor inverts vs pick 5's 75; 80 last 6.9, How-to 320
    7: 600.0,
    8: 750.0,   # Off 750. Was 1000 (flat with 9/10). Climb 8<9<10. How-to 3000
    9: 900.0,   # Off 900. Was 1000. How-to 3600
    10: 1000.0, # Off 1000. Classic ceiling. How-to 4000
}

# Earn medium: Pulse x2, Lumen x2, How-to = advertised x4. Tops are the
# How-to floor vs Off (or the first lock-clean last-catch) so the HUD does
# not park the body then cliff into the jackpot. Pick 7 already last-steps
# at 9x. Pick 10 cannot lock-clean the 8->9 mid at any top.
MEDIUM_EARN_TOP = {
    3: 32.3,    # Off 60.3. 2-hit matches Off 1.7x (a real win, not a 1.0 push); RTP 0.9646
    4: 44.5,    # Off 174.9. 110 left a 73x last step (1.5 -> 110); 44.5 How-to 178, 3-hit 6.9 (HUD 7)
    5: 154.5,   # Off 450. 406.5 left 2.6 -> 406.5 (156x); 154.5 is first lock-clean, 4-hit 20.2, last 7.65
    6: 162.5,   # Off 650. 650 left 29.9 -> 650 (22x); How-to floor 650, last 4.03
    7: 750.0,   # Off 750. Last step 9x already in band
    8: 2000.0,  # Off 2500. 5000 left 168 -> 5000 (30x); 2000 is lock-clean last 8.9, How-to 8000
    9: 3000.0,  # Off 4000. 5000 left 225 -> 5000 (22x); 3000 is lock-clean last 13.3, How-to 12000
    10: 4000.0,  # Off 5000. Must sit above pick 9's 3000 (HUD 8<9<10). Last 17.8; 5000 was 22x.
}

# Earn high: Pulse x2, Lumen x2, How-to = advertised x4. Skip JACKPOT_TOP
# (100000 advertised is the old solver pin, not this HUD copy). Dashboard
# MAX_PAYOUT_ABS[1.0]=100000 so advertised * 4 <= 100000, advertised <= 25000.
# Off pick 10 is 50000; Earn cannot pin 50000 (How-to would be 200000).
# 9/9 pins 12500 (not 25000) so the HUD climbs 6100 < 12500 < 25000; a flat
# 25000 = 25000 made 9/9 the equal of 10/10 for 5x the catch odds.
HIGH_EARN_TOP = {
    2: 11.9,      # Off 16.7 blows RTP; max in-window. How-to 47.6 >= Off
    3: 35.1,      # Off 71.6 blows RTP/hit/etl; How-to 140.4 >= Off
    4: 122.5,     # Off 382.4 blows etl40; How-to 490 >= Off
    5: 229.3,     # Off 900 (std envelope). Was 439.3: 2.1 -> 439.3 was a
                  # 209x cliff. 229.3 gives 15.5 -> 229.3 (14.8x), How-to
                  # 917.2 >= Off 900. Row pinned as a restair.
    6: 552.8,     # Off 2200. Was 2028.7: 1.8 -> 2028.7 was a 1127x cliff.
                  # 552.8 gives 55.2 -> 552.8 (10.0x), How-to 2211.2 >= Off.
                  # Row pinned as a restair.
    7: 1468.8,    # Off 5500. Was 4582: 75.8 -> 4582 was a 60x cliff.
                  # 1468.8 gives 144.1 -> 1468.8 (10.2x), How-to 5875.2 >=
                  # Off 5500. Row pinned as a restair.
    8: 6100.0,    # Off 6100 (std envelope). Old 11122.6 sat over Off.
    9: 12500.0,   # Off 40000; was 25000 (flat with 10). How-to 50000 > Off
    10: 25000.0,  # Off 50000; cannot pin 50000 (How-to 200000 vs 100k cap)
}


def is_easy_earn_low(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    return bool(earn and buy is None and risk == "low" and cost == 1.0)


def is_easy_earn_classic(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    return bool(earn and buy is None and risk == "classic" and cost == 1.0)


def is_easy_earn_medium(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    return bool(earn and buy is None and risk == "medium" and cost == 1.0)


def is_easy_earn_high(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    return bool(earn and buy is None and risk == "high" and cost == 1.0)


def is_easy_buy_low(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    """Buy low Easy analogue: extras + placed Lumen; tops may exceed Off."""
    return bool(earn and risk == "low" and buy in ("buy10", "buy100") and cost in (10.0, 100.0))


def is_easy_buy_classic(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    """Buy classic Easy analogue: extras + placed Lumen; tops may exceed Off."""
    return bool(
        earn and risk == "classic" and buy in ("buy10", "buy100") and cost in (10.0, 100.0)
    )


def is_easy_buy_medium(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    """Buy medium: extras + catch, not a raised jackpot."""
    return bool(
        earn and risk == "medium" and buy in ("buy10", "buy100") and cost in (10.0, 100.0)
    )


def is_easy_buy_high(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    """Buy high: extras + catch, not a raised jackpot."""
    return bool(
        earn and risk == "high" and buy in ("buy10", "buy100") and cost in (10.0, 100.0)
    )


def easy_buy_low_top(k: int, cost: float) -> float | None:
    """Cost-unit advertised pin from easy_buy_low.JSON_MAX_LADDER.

    Tops are *not* pinned to Off Easy max. Picks 4–10 sit above Off Easy
    (buy bonus); picks 2–3 stay at 2.6 under placed Lumen. How-to vs debit is
    JSON_top * Lumen * Pulse / cost = 2 * JSON_top, capped at Earn Easy 400x
    on picks 8–10 (pick 10 JSON 200 → 400x with Pulse).
    """
    if k not in JSON_MAX_LADDER:
        return None
    return floor_grid(JSON_MAX_LADDER[k] / cost, cost)


def easy_buy_classic_top(k: int, cost: float) -> float | None:
    """Cost-unit advertised pin from easy_buy_classic.JSON_MAX_LADDER.

    Tops are *not* pinned to Off classic max. Picks 6–10 sit above Off
    classic on buy10 (buy bonus); buy100 deep picks floor at the Max Payout
    pin (JSON 450). How-to vs debit is 2 x JSON, capped at Earn classic
    How-to on picks 8–10 (pick 10 JSON 2000 → 4000x with Pulse).
    """
    if k not in CLASSIC_BUY_JSON_MAX_LADDER:
        return None
    return floor_grid(classic_buy_json_max_for(k, cost) / cost, cost)


def easy_buy_medium_top(k: int, cost: float) -> float | None:
    """Cost-unit advertised pin from easy_buy_medium.JSON_MAX_LADDER.

    Tops are *not* pinned to Off medium max — gradual mid→top under placed
    Lumen. Max Payout floors buy100 deep picks (JSON ≤ 450).
    """
    if k not in MEDIUM_BUY_JSON_MAX_LADDER:
        return None
    return floor_grid(medium_buy_json_max_for(k, cost) / cost, cost)


def easy_buy_high_top(k: int, cost: float) -> float | None:
    """Cost-unit advertised pin from easy_buy_high.JSON_MAX_LADDER.

    Tops are *not* pinned to Off high max — gradual mid→top under placed
    Lumen. Max Payout floors buy100 deep picks (JSON ≤ 450).
    """
    if k not in HIGH_BUY_JSON_MAX_LADDER:
        return None
    return floor_grid(high_buy_json_max_for(k, cost) / cost, cost)


def skip_jackpot_for_easy_low(
    risk: str, earn: bool, buy: str | None, cost: float
) -> bool:
    return (
        is_easy_earn_low(risk, earn, buy, cost)
        or is_easy_earn_classic(risk, earn, buy, cost)
        or is_easy_earn_medium(risk, earn, buy, cost)
        or is_easy_earn_high(risk, earn, buy, cost)
        or is_easy_buy_low(risk, earn, buy, cost)
        or is_easy_buy_classic(risk, earn, buy, cost)
        or is_easy_buy_medium(risk, earn, buy, cost)
        or is_easy_buy_high(risk, earn, buy, cost)
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

# Pinned top-hit prize, settled, in multiples of the mode cost. Unlike every
# other row this one is *set* rather than water-filled, and it is deliberately
# outside the CAP_FRACTION ladder so it cannot lift the tiers below it.
#
# Why a separate mechanism. The water-fill shape is m_h = c * coeff(h)^-beta,
# so raising a cap does nothing on its own: high_pick_10 solves to c ~ 4.5e-5
# and c * p^-0.9 lands at ~4,860x whatever the ceiling says. On low (beta 0.35)
# the shape is flat enough that the full card settles at 9.6x on Earn against
# 400x on Off — turning bonuses on used to *lower* the visible ceiling 40x.
# Both are the same defect: nothing in the solver was choosing the headline.
#
# Why picks 4-10 and not 1-3. The water-fill's exponential never reaches the
# risk ceiling on a flat beta (low pick 8 solved to 3.6x against a 400x cap),
# so the advertised max on those modes was an artifact. Pinning the full-card
# row restores a declared number. Picks 1-3 cannot hold a pin: pick_1 is the
# two-outcome lattice, and on 2-3 the top row is load-bearing for Earn RTP, so
# a pin undershoots the band. Pick 4 is the first row whose p(top) is small
# enough that a round ceiling still leaves mid-tier budget; CVaR ≈ the top
# there, so high is pinned at 350x against the 700 gate (probe max 353).
#
# Volatility, not RTP, is the binding constraint below pick 9. Binary search
# against Off+Earn with the observed-safe std 18.3 (not the hard 55 gate) gives
# the envelope this ladder is designed inside:
#
#   max pin | pick 4 | pick 5 | pick 6 | pick 7 | pick 8
#   low     |    324 |    935 |  2,471 |  6,105 |  7,218
#   classic |    382 |    934 |  2,464 |  5,924 | 14,703
#   medium  |    382 |    912 |  2,361 |  6,689 | 17,974
#   high    |    366 |    907 |  2,290 |  5,607 |  6,122
#
# Two properties of that envelope drive the shape below.
#
# It is nearly risk-independent at picks 4-6 (~370 / ~920 / ~2,400 for every
# risk) because the std cap binds on the top row itself and p(h == k) is the
# same hypergeometric for all four risks. The risk dial therefore cannot be
# expressed by pushing each risk to its own maximum — low deliberately sits far
# under its own ceiling so low < classic < medium < high stays meaningful.
#
# It stops growing for `high` at pick 8 (5,607 -> 6,122, only 1.09x) while
# low/classic/medium keep climbing to 7,218-17,974. Because the ladder must also
# be risk-ordered, `high`'s ceiling caps every risk at pick 8, which compresses
# the risk spread from 7x at pick 4 to 3x at pick 8. That is the volatility
# envelope, not a design choice: variance is p * m^2, p falls ~11x from pick 7
# to pick 8, and `high`'s mid rows already spend more of the budget.
#
# The rule applied here: **take the largest round value under the envelope that
# keeps the top strictly increasing in k and ordered across risk.** Strict
# monotonicity in k is the property the first version of this table got wrong —
# it pinned low to 400x at picks 6, 7 *and* 8, so an 8-of-8 (1 in 1,708,993)
# paid exactly what a 6-of-6 (1 in 18,278) paid, 94x rarer for the same prize.
# A plateau anywhere on this ladder is a bug: the full card gets monotonically
# rarer in k, so its prize must too.
#
# Growth per pick lands at ~2-3x through the mid ladder and steepens to 4-5x
# into picks 9-10, which tracks how rarity accelerates (6x per pick at 4->5,
# 31x at 9->10). The one soft spot is high 7 -> 8 at 1.2x, forced by the 6,122
# ceiling above; lowering high pick 7 to 4,000x would smooth it at the cost of a
# real advertised maximum, so the flat-ish step is kept and documented.
#
# high pick 6 stays 2,000x (`TOP_OVERRIDE` records the same value) — it was rated
# Extreme at 3,373x / std 25.73, so it is held under its 2,290x probe ceiling.
#
# Frequencies cannot move. The set of paying tiers is untouched, so hit, win,
# LDW and push rates are identical before and after by construction — only the
# ceiling and a rounding-level slice of the mid rows change.
#
# Values keep the risk dial ordered (low < classic < medium < high) so "high
# risk" still means the largest ceiling, and top out at 100,000x: the 3-Star Max
# Payout Multiplier exactly, and the top of the 50,000-100,000x range third-party
# listings claim for Keno Xtreme. See [[domain/stake-rating-limits]] and
# [[sources/keno-xtreme-analysis]].
#
# The buy chips do not reach the 4-8 Off/Earn pins — those values are cost-1
# headlines, and applying them as cost-units on a 1-in-435 row blows RTP.
# Picks 9-10 stay pinned on every kind so the chip still advertises
# MAX_PAYOUT_ABS / cost (4,500x buy10, 900x buy100).
JACKPOT_TOP = {
    ("low", 4): 50.0,
    ("low", 5): 150.0,
    ("low", 6): 400.0,
    ("low", 7): 1_000.0,
    ("low", 8): 2_000.0,
    ("low", 9): 4_000.0,
    ("low", 10): 20_000.0,
    ("classic", 4): 100.0,
    ("classic", 5): 300.0,
    ("classic", 6): 800.0,
    ("classic", 7): 2_000.0,
    ("classic", 8): 3_500.0,
    ("classic", 9): 8_000.0,
    ("classic", 10): 40_000.0,
    ("medium", 4): 200.0,
    ("medium", 5): 600.0,
    ("medium", 6): 1_500.0,
    ("medium", 7): 3_000.0,
    ("medium", 8): 5_000.0,
    ("medium", 9): 15_000.0,
    ("medium", 10): 60_000.0,
    ("high", 4): 350.0,
    ("high", 5): 900.0,
    ("high", 6): 2_000.0,
    ("high", 7): 5_000.0,
    # Pinned at the pick-8 probe ceiling of 6,122x, the tightest value in the
    # whole table. Every other risk's pick-8 top is ordered under this one.
    ("high", 8): 6_000.0,
    ("high", 9): 25_000.0,
    # Sits *on* the 3-Star Max Payout Multiplier, not under it — the deliberate
    # exception to this file's design-below-the-maximum rule, taken because the
    # headline is the whole point of the mode. `check_gates` uses `>`, so exactly
    # 100,000x passes locally, and the advertised row is grid-floored before the
    # settle multiply so Earn cannot drift over. If the dashboard ever rejects it
    # (a `>=` read, or a rounding difference in `max_win`), drop straight back to
    # 90,000x — nothing else in the ladder depends on this value.
    ("high", 10): 100_000.0,
}

# The two shape rules above are cheap to state and easy to break by hand — the
# first version of this table plateaued low at 400x across picks 6, 7 and 8. Fail
# at import rather than solving 160 tables around a ladder that pays a rarer full
# card the same as a commoner one.
RISK_ORDER = ("low", "classic", "medium", "high")


def _assert_jackpot_ladder_distributed() -> None:
    for risk in RISK_ORDER:
        pins = sorted(
            (k, m) for (r, k), m in JACKPOT_TOP.items() if r == risk
        )
        for (k_lo, m_lo), (k_hi, m_hi) in zip(pins, pins[1:]):
            if m_hi <= m_lo:
                raise AssertionError(
                    f"JACKPOT_TOP {risk} is not increasing in picks: "
                    f"pick {k_lo} pays {m_lo:.0f}x and pick {k_hi} pays "
                    f"{m_hi:.0f}x, but the pick-{k_hi} full card is rarer"
                )
    for k in {k for _, k in JACKPOT_TOP}:
        row = [
            (risk, JACKPOT_TOP[(risk, k)])
            for risk in RISK_ORDER
            if (risk, k) in JACKPOT_TOP
        ]
        for (r_lo, m_lo), (r_hi, m_hi) in zip(row, row[1:]):
            if m_hi <= m_lo:
                raise AssertionError(
                    f"JACKPOT_TOP pick {k} is not ordered by risk: "
                    f"{r_lo} pays {m_lo:.0f}x, {r_hi} pays {m_hi:.0f}x"
                )


_assert_jackpot_ladder_distributed()

# Pinning the top row alone is not enough: it raises the headline without raising
# anything beneath it, and on a flat beta the water-fill leaves the approach
# level. low pick 8 shipped as 1.9 / 2.1 / 2.5 / 2.6 / 2.7 / 2,000x — a 741x
# final step, where 7-of-8 (1 in 21,363) paid 2.7x.
#
# The published guidance is that a prize ladder should be geometric; Vercel-era
# slot-math writing quotes 1.5-2.5x between adjacent premium tiers. Keno's
# probability ratios between adjacent hit counts are far steeper than a slot's
# symbol tiers, so that band is too tight to apply literally. The calibration
# used instead is the Stake Keno reference matrix extracted from
# `wiki/sources/stake_keno_probability_payout_analysis.docx`, which across all
# 30 of its ladders never steps more than 31.8x, and whose *final* step onto the
# full card is 1.2-8x.
#
# So: cap the final steps. `_fill_from` pins the rows below the jackpot to
# jackpot / step when the fill leaves them further down than this, walking down
# at most DESCENT_DEPTH rows and skipping any pin it cannot afford.
#
# Per risk, because the shape means different things per risk. Stake's own
# descent is steep on low (1000 -> 250 -> 50, i.e. 4x then 5x) and shallow on
# high (1000 -> 800 -> 500, 1.25x then 1.6x): high risk should already be paying
# heavily one row down, low should keep its value in the top row. Ours are
# steeper than Stake's throughout because our headline is Xtreme-scale
# (100,000x) against their 1,000x, so there is much further to descend.
MAX_FINAL_STEP = {"low": 8.0, "classic": 8.0, "medium": 6.0, "high": 5.0}

# Three rows is enough to turn a cliff into a run without reaching down into the
# mid tiers that actually carry the RTP (the full-card row is under 0.4% of RTP
# at picks 6-10, so the budget has to come from somewhere, and it should not come
# from the rows the player hits often).
DESCENT_DEPTH = 3

# A descent row is only cheap if it is rare. high pick 6's 5-of-6 is 1 in 508, so
# pinning it to 2,000/5 = 400x costs 82% of the mode's RTP and loads ETL40 to
# 0.897 against a 0.88 gate — the row stops being an approach to the jackpot and
# becomes the game. The rows this is meant to fix are far rarer: low pick 8's
# 7-of-8 pin is 1.2% of RTP, high pick 10's 9-of-10 pin is 0.7%.
#
# So bound the pin by EV share, which is the diagnostic the keno calculators and
# the F2P prize-structure guidance both use for an aspirational tier. Modes that
# cannot buy a smooth approach keep their step and are reported as-is rather than
# being solved into a gate failure.
#
# 0.25 rather than 0.10 because low pick 6 needs 10.2% to reach its 50x pin and
# was the only mode the tighter bound rejected; high pick 6 wants 82% and is
# still refused by a wide margin.
DESCENT_MAX_EV_SHARE = 0.25

# The descent moves budget into rarer rows, which is a variance trade by
# construction. Left unbounded it took high_pick_10_earn from std 11.99 to 32.60
# — past the 25.73 the dashboard was observed to label EXTREME
# ([[domain/stake-rating-limits]]) — so a smoother paytable would have bought a
# worse rating on the flagship mode.
#
# 18.3 is the highest std this repo has seen ship unflagged. Modes already above
# it keep their own value as the ceiling, so the descent can never make a hot
# mode hotter; it just stops pinning when it would.
DESCENT_MAX_SD = 18.3

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
    # Off/Earn now sit exactly here: JACKPOT_TOP pins high pick 10 to 100,000x,
    # so this is a binding ceiling rather than the uniformity placeholder it was
    # while the ladder peaked at 4,900x. 3-Star only — 2-Star's 50,000x cannot
    # carry this mode.
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
    # Per-cost settled ceiling. Raised from 10,000 when JACKPOT_TOP landed: it
    # was a hand-picked round number, not a published limit, and it would have
    # rejected the pinned ladder before the dashboard ever saw it. The gate that
    # actually exists is MAX_PAYOUT_ABS, measured against the base bet.
    "max_m": 100000.0,
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


def cap_for(
    risk: str,
    k: int,
    h: int,
    cost: float = 1.0,
    allow_descent: bool = True,
    use_jackpot: bool = True,
) -> float:
    """Settled (after Lumen) ceiling for advertised hit h, in units of `cost`.

    The third term is the dashboard's Max Payout Multiplier. It has to be
    divided by `cost` because the ladder is solved in cost units and scaled up
    on export, so a ceiling that looks modest here is `cost` times larger
    against the base bet the gate measures.
    """
    payout_cap = MAX_PAYOUT_ABS[cost] / cost
    # A pinned jackpot answers only to the payout gate. Keeping it out of the
    # CAP_FRACTION ladder is the point: were it the ladder's base, a 100,000x
    # headline would raise the 9-of-10 cap from 2,500x to 60,000x and the
    # water-fill would spend the mode's whole budget one row down.
    if (
        use_jackpot
        and h == k
        and (risk, k) in JACKPOT_TOP
        and jackpot_applies(k, cost)
    ):
        return min(JACKPOT_TOP[(risk, k)], payout_cap)
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
    base = min(top * CAP_FRACTION[dist], CAP_ABSOLUTE[dist])
    # The rows just under a pinned jackpot need headroom for the descent that
    # keeps the final steps inside MAX_FINAL_STEP. CAP_ABSOLUTE is precisely what
    # flattened them — it held 7-of-8 to 1,000x while the top row was pinned at
    # 2,000x, and the fill then left it at 2.7x. Deriving the allowance from the
    # same ratio the descent uses keeps this function agreeing with `_fill_from`,
    # so the validator accepts a pinned row instead of reporting a cap violation.
    #
    # `allow_descent=False` is what the fill passes for rows it is *not* pinning.
    # Granting the window unconditionally let the ordinary water-fill spend into
    # headroom no pin had asked for and nothing had validated, which took
    # high_pick_10_earn to std 32.60 — past the observed EXTREME threshold — with
    # the descent's own volatility guard never consulted.
    if (
        use_jackpot
        and allow_descent
        and h != k
        and (risk, k) in JACKPOT_TOP
        and jackpot_applies(k, cost)
        and k - h <= DESCENT_DEPTH
    ):
        base = max(base, JACKPOT_TOP[(risk, k)] / MAX_FINAL_STEP[risk] ** (k - h))
    return min(base, payout_cap)


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
    `placed` marks Lumen on a pick; catch is hit-or-miss (not forced into the ten).
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
    allow_descent: bool = True,
) -> float:
    """Advertised ceiling so the settled prize stays under `cap_for`."""
    if is_easy_earn_low(risk, earn, buy, cost) and h == k and k in EASY_EARN_LOW_TOP:
        return EASY_EARN_LOW_TOP[k]
    if is_easy_earn_classic(risk, earn, buy, cost) and h == k and k in CLASSIC_EARN_TOP:
        return CLASSIC_EARN_TOP[k]
    if is_easy_earn_medium(risk, earn, buy, cost) and h == k and k in MEDIUM_EARN_TOP:
        return MEDIUM_EARN_TOP[k]
    if is_easy_earn_high(risk, earn, buy, cost) and h == k and k in HIGH_EARN_TOP:
        return HIGH_EARN_TOP[k]
    if is_easy_buy_low(risk, earn, buy, cost) and h == k:
        pin = easy_buy_low_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_classic(risk, earn, buy, cost) and h == k:
        pin = easy_buy_classic_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_medium(risk, earn, buy, cost) and h == k:
        pin = easy_buy_medium_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_high(risk, earn, buy, cost) and h == k:
        pin = easy_buy_high_top(k, cost)
        if pin is not None:
            return pin
    return floor_grid(
        cap_for(
            risk,
            k,
            h,
            cost,
            allow_descent,
            use_jackpot=not skip_jackpot_for_easy_low(risk, earn, buy, cost),
        )
        / settle_factor(risk, earn, buy),
        cost,
    )


def jackpot_applies(k: int, cost: float = 1.0) -> bool:
    """Whether JACKPOT_TOP is a target for this kind, not just a cap.

    Picks 4-8 are Off/Earn headlines in cost-1 units. Reusing them as
    cost-units on a buy turns a 1-in-435 row into 80pp of RTP (buy10 high
    pick 4). Picks 9-10 stay pinned on every kind so the chip still
    advertises `MAX_PAYOUT_ABS / cost`.
    """
    if cost == 1.0:
        return True
    return k >= 9


def jackpot_advertised(
    risk: str, k: int, earn: bool = True, cost: float = 1.0, buy: str | None = None
) -> float | None:
    """Advertised top-hit row for a pinned-jackpot mode, else None.

    Same value `advertised_cap` returns at `h == k`, named separately because
    here it is a target rather than a ceiling: the row is set to it and then
    held out of the water-fill.
    """
    if is_easy_earn_low(risk, earn, buy, cost) and k in EASY_EARN_LOW_TOP:
        return EASY_EARN_LOW_TOP[k]
    if is_easy_earn_classic(risk, earn, buy, cost) and k in CLASSIC_EARN_TOP:
        return CLASSIC_EARN_TOP[k]
    if is_easy_earn_medium(risk, earn, buy, cost) and k in MEDIUM_EARN_TOP:
        return MEDIUM_EARN_TOP[k]
    if is_easy_earn_high(risk, earn, buy, cost) and k in HIGH_EARN_TOP:
        return HIGH_EARN_TOP[k]
    if is_easy_buy_low(risk, earn, buy, cost) and k >= 4:
        pin = easy_buy_low_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_classic(risk, earn, buy, cost) and k >= 2:
        # Raised JSON_MAX_LADDER pins (easy_buy_classic.py), not Off classic.
        pin = easy_buy_classic_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_medium(risk, earn, buy, cost) and k >= 2:
        # Gradual JSON_MAX_LADDER pins (easy_buy_medium.py), not Off medium.
        pin = easy_buy_medium_top(k, cost)
        if pin is not None:
            return pin
    if is_easy_buy_high(risk, earn, buy, cost) and k >= 2:
        # Gradual JSON_MAX_LADDER pins (easy_buy_high.py), not Off high.
        pin = easy_buy_high_top(k, cost)
        if pin is not None:
            return pin
    if (risk, k) not in JACKPOT_TOP or not jackpot_applies(k, cost):
        return None
    return advertised_cap(risk, k, k, earn, cost, buy)


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
        else base_stats(k, table, risk)
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
    m: list[float],
    start: int,
    k: int,
    caps: dict,
    cost: float = 1.0,
    held: frozenset[int] = frozenset(),
):
    """Single +/-step moves that keep floors, caps and monotonicity.

    `held` rows are pinned (the jackpot) and are never offered as a move, so
    the RTP residual is absorbed by the rows a player actually reaches.
    """
    step = grid_step(cost)
    for h in range(start, k + 1):
        if h in held:
            continue
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
    held: frozenset[int] = frozenset(),
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
        for h, d in _grid_moves(m, start, k, caps, cost, held):
            new_err = best_err + d * p[h]
            if abs(new_err) < abs(best_err) - 1e-12:
                m[h] = round(m[h] + d, 10)
                best_err = new_err
                improved = True
        if improved:
            continue
        # No single move helps: try pairs (+step on one tier, -step on another).
        pair = None
        for h1, d1 in _grid_moves(m, start, k, caps, cost, held):
            if abs(d1 - step) > 1e-12:
                continue
            for h2, d2 in _grid_moves(m, start, k, caps, cost, held):
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


def _fill_once(
    risk: str,
    k: int,
    start_pay: float | None,
    earn: bool = True,
    bought: bool = False,
    cost: float = 1.0,
    placed: bool = False,
    cap_overrides: dict[int, float] | None = None,
    buy: str | None = None,
    pins: dict[int, float] | None = None,
) -> list[float]:
    """Water-fill + grid-converge with a fixed (or designed) consolation pay.

    `pins` are descent rows below the jackpot, fixed by `_fill_from` and held out
    of the fill exactly like the jackpot row.
    """
    p = pay_coeff(risk, k, earn, bought, placed, buy, cost)
    beta = RISK_SHAPES[risk]["beta"]
    start = PAY_START[risk][k]
    # Only the rows this trial pins get the descent window. Every other row is
    # capped as if the descent did not exist, so unpinned headroom cannot be spent.
    pinned = set(pins or ())
    caps = {
        h: advertised_cap(risk, k, h, earn, cost, buy, allow_descent=h in pinned)
        for h in range(start, k + 1)
    }
    if cap_overrides:
        caps = {h: min(v, cap_overrides[h]) if h in cap_overrides else v for h, v in caps.items()}
    # The jackpot row is pinned at its cap, spends its (tiny) budget alongside
    # the refund tier, and leaves the water-fill. An `etl_sum` shrink arrives
    # here as a cap override, so it still lowers the pin rather than being
    # ignored — `solve_table` then reports the mode instead of shipping a
    # headline the ladder did not deliver.
    jackpot = caps[k] if jackpot_advertised(risk, k, earn, cost, buy) is not None else None
    held = frozenset({k}) if jackpot is not None else frozenset()
    # Descent pins are held exactly like the jackpot. They stay inside `caps`
    # because `cap_for` already grants the descent window its headroom.
    descent = {h: v for h, v in (pins or {}).items() if start < h < k}
    if jackpot is not None and descent:
        held |= frozenset(descent)
    else:
        descent = {}
    tail = [h for h in range(start + 1, k + 1) if h not in held]
    rh = refund_hit(risk, k, earn, bought, placed, buy, cost)
    rx = refund_pay(risk, cost, buy, earn)
    refund_cost = p[rh] * rx if rh is not None else 0.0
    jackpot_cost = p[k] * jackpot if jackpot is not None else 0.0
    jackpot_cost += sum(p[h] * v for h, v in descent.items())
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
        math.floor(
            (RTP_TARGET - refund_cost - jackpot_cost) / p[start] * _grid_ticks(cost)
            - 1e-9
        )
        / _grid_ticks(cost),
    )

    m = [0.0] * (k + 1)
    if rh is not None:
        m[rh] = rx
    if jackpot is not None:
        m[k] = jackpot
    for h, v in descent.items():
        m[h] = v
    m[start] = m_start
    remaining = RTP_TARGET - p[start] * m[start] - refund_cost - jackpot_cost

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
        if h in held:
            continue
        if m[h] > 0:
            m[h] = floor_grid(m[h], cost)
            m[h] = max(min_start if h == start else step, m[h])

    coin_rows = [h for h in range(start, k + 1) if h not in held]
    for _ in range(max(2000, int(round(200 / step)))):
        leftover = RTP_TARGET - rtp()
        if abs(leftover) <= RTP_TOL:
            break
        if leftover < 0:
            best = None
            for h in coin_rows:
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
        for h in coin_rows:
            coin = p[h] * step
            ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - step)
            if m[h] + step > ceiling + 1e-9:
                continue
            if coin <= leftover + 1e-12 and (best is None or coin > best[0]):
                best = (coin, h)
        if best is None:
            for h in coin_rows:
                coin = p[h] * step
                ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - step)
                if m[h] + step > ceiling + 1e-9:
                    continue
                if best is None or coin < best[0]:
                    best = (coin, h)
        if best is None:
            break
        m[best[1]] = round(m[best[1]] + step, 10)

    _refine(m, p, start, k, caps, cost, held)
    return m


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
    """Water-fill, then flatten any cliff below the pinned jackpot.

    Fills once, then walks down from the top row pinning any step steeper than
    MAX_FINAL_STEP to `row above / step`. Each pin is re-filled rather than
    patched in, so the budget it spends is taken out of the tail by the same
    water-fill that produced the rest of the ladder.
    """
    args = (risk, k, start_pay, earn, bought, cost, placed, cap_overrides, buy)
    m = _fill_once(*args)
    if jackpot_advertised(risk, k, earn, cost, buy) is None:
        return m

    start = PAY_START[risk][k]
    p = pay_coeff(risk, k, earn, bought, placed, buy, cost)
    limit = MAX_FINAL_STEP[risk]
    caps = {h: advertised_cap(risk, k, h, earn, cost, buy) for h in range(start, k + 1)}

    def sd_of(table: list[float]) -> float:
        return mode_stats_for(
            risk, k, table, earn, bought, placed, cost, buy
        )["std"]

    sd_ceiling = max(DESCENT_MAX_SD, sd_of(m))

    def usable(trial: list[float]) -> bool:
        """Whether a pinned fill is still a shippable ladder.

        The pin's budget comes out of the tail, so an unaffordable pin shows up
        as a negative row, a dip, or an RTP miss rather than as an error. Judge
        the trial instead of predicting the cost: a mode that cannot afford a
        smooth approach keeps its cliff and stays inside its band.
        """
        if any(x < 0 for x in trial):
            return False
        if abs(sum(pi * xi for pi, xi in zip(p, trial)) - RTP_TARGET) > RTP_TOL:
            return False
        paying = [x for x in trial if x > 0]
        if any(b < a for a, b in zip(paying, paying[1:])):
            return False
        return sd_of(trial) <= sd_ceiling

    pins: dict[int, float] = {}
    for h in range(k - 1, max(start, k - 1 - DESCENT_DEPTH), -1):
        if h <= start or m[h] <= 0 or m[h + 1] <= 0:
            break
        if m[h + 1] / m[h] <= limit:
            break
        ideal = min(floor_grid(m[h + 1] / limit, cost), caps[h])
        if p[h] * ideal > DESCENT_MAX_EV_SHARE * RTP_TARGET:
            ideal = floor_grid(DESCENT_MAX_EV_SHARE * RTP_TARGET / p[h], cost)
        if ideal <= m[h]:
            break
        # Best effort rather than all-or-nothing. low pick 8 cannot fund the full
        # 31.25x pin on its 6-of-8 row — its tail is a flat 1.9-2.4 run with
        # nothing to give back — but it can fund a smaller one, and a 16x step is
        # worth having even when 8x is out of reach.
        best: tuple[float, list[float]] | None = None
        lo, hi = m[h], ideal
        for _ in range(24):
            target = floor_grid((lo + hi) / 2, cost)
            if target <= m[h] or hi - lo <= grid_step(cost):
                break
            trial = _fill_once(*args, pins={**pins, h: target})
            if trial[h] >= target - 1e-9 and usable(trial):
                best = (target, trial)
                lo = target
            else:
                hi = target
        full = _fill_once(*args, pins={**pins, h: ideal})
        if full[h] >= ideal - 1e-9 and usable(full):
            best = (ideal, full)
        if best is None:
            break
        pins[h] = best[0]
        m = best[1]
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
    # A declared jackpot is a published number, so it fails loudly rather than
    # drifting: the etl_sum shrink above and any cap override reach the pin
    # through `caps`, and a mode that cannot afford its headline should be
    # retuned in JACKPOT_TOP, not quietly shipped a row lower.
    declared = jackpot_advertised(risk, k, earn, cost, buy)
    if declared is not None and abs(m[k] - declared) > 1e-9:
        settled_note = ""
        if (risk, k) in JACKPOT_TOP:
            settled_note = f" (settled {JACKPOT_TOP[(risk, k)]:.0f}x of cost)"
        errors.append(
            f"jackpot row {m[k]:.4f} != declared {declared:.4f}{settled_note}"
        )
    return m, errors


def mode_stats(risk: str, k: int, table: list[float]) -> dict:
    return settled_stats(risk, k, table)


def check_gates(
    k: int,
    stats: dict,
    *,
    earn: bool = False,
    cost: float = 1.0,
    risk: str | None = None,
) -> list[str]:
    f: list[str] = []
    lo, hi = MODE_RTP_BAND
    # Off pick_1 advertised pair sits on the two-outcome 0.025 lattice
    # (0.950). Risks without the miss-bonus third tier would be exempt
    # from the band; every shipped risk now carries the bonus and must
    # land on target (dashboard Cross-Mode includes pick_1).
    if k == 1 and not earn and risk is not None and not has_pick_one_bonus(risk):
        if abs(stats["rtp"] - PICK_ONE_BASE_RTP) > 1e-9:
            f.append(
                f"advertised rtp={stats['rtp']:.4f} != {PICK_ONE_BASE_RTP:.4f} "
                "two-outcome lattice"
            )
    else:
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
    # k >= 2 needs at least two paying tiers, except Off `high` pick 2:
    # the Hard HUD pays only 2/2 (jackpot-or-bust). One advertised cell is
    # the designed shape, not a degenerate table.
    if len(stats["nonzero_payouts"]) < 2:
        if not (risk == "high" and k == 2 and not earn and cost == 1.0):
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

    pick_1 places Lumen on the only pick (hit-or-miss, not forced). Catching
    that pick is 10/40; a hit always pays BUY_LUMEN_BOOST because h=1 ⇒ mark hit.
    """
    paying = frozenset({0, 1})
    placed = lumen_placed_on_pick(buy, 1)
    p = effective_coeff(risk, 1, paying, True, placed, buy)
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
            rtp = settled_rtp(risk, 1, table, True, placed, buy, cost)
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
            elif not earn and risk == "low" and not bought and buy is None:
                # Off `low` is the Keno Xtreme Easy analogue: a designed HUD
                # copy (easy_off_low.py), not a water-fill solve.
                table, errors = list(EASY_OFF_LOW[k]), []
            elif earn and risk == "low" and not bought and buy is None:
                # Earn `low`: leftover-share of the Easy HUD with Lumen/Pulse
                # priced in (easy_earn_low.py). Buy chips keep their own ladders.
                table, errors = list(EASY_EARN_LOW[k]), []
            elif earn and risk == "low" and bought and buy in BUY_COSTS and k >= 2:
                # Buy `low` Easy analogue (easy_buy_low.py): bought extras +
                # placed Lumen (BUY_LUMEN_BOOST) + Pulse, JSON chart shared by
                # buy10/buy100. pick_1 stays on buy_pick_one_row above.
                table, errors = easy_buy_cost_row(k, buy), []
            elif earn and risk == "classic" and bought and buy in BUY_COSTS and k >= 2:
                table, errors = easy_buy_classic_cost_row(k, buy), []
            elif earn and risk == "medium" and bought and buy in BUY_COSTS and k >= 2:
                # Buy medium gradual charts (easy_buy_medium.py) — buy10 and
                # separate buy100 ladder under 100× Lumen.
                table, errors = easy_buy_medium_cost_row(k, buy), []
            elif earn and risk == "high" and bought and buy in BUY_COSTS and k >= 2:
                table, errors = easy_buy_high_cost_row(k, buy), []
            elif not earn and risk == "classic" and not bought and buy is None:
                # Off `classic`: max-anchored geometric ladder (easy_off_classic.py).
                # pick_1 stays on the lattice.
                table, errors = list(CLASSIC_OFF[k]), []
            elif not earn and risk == "medium" and not bought and buy is None:
                table, errors = list(MEDIUM_OFF[k]), []
            elif not earn and risk == "high" and not bought and buy is None:
                table, errors = list(HIGH_OFF[k]), []
            else:
                table, errors = solve_table(
                    risk, k, earn, bought, cost, placed, buy
                )
            stats = mode_stats_for(risk, k, table, earn, bought, placed, cost, buy)
            fails = errors + check_gates(k, stats, earn=earn, cost=cost, risk=risk)
            if (
                not earn
                and risk == "high"
                and k == 2
                and not bought
                and buy is None
            ):
                # Hard HUD pick 2 pays only the 2-hit; zero prefix forbids a
                # second advertised tier.
                fails = [
                    f for f in fails if "fewer than 2 nonzero payouts" not in f
                ]
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
        # Off pick_1's third tier (every risk). Both miss amounts are
        # advertised, so the client needs the bonus pay and its odds.
        "pick1Bonus": {
            "weight": PICK_ONE_BONUS_WEIGHT,
            "missWeight": MISS_WEIGHT,
            "total": MISS_WEIGHT + HIT_WEIGHT,
            "pay": {
                risk: pick_one_bonus_miss(risk)
                for risk in PICK_ONE_BONUS_RISKS
            },
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


def patch_earn_low(paytables_path: str | None = None) -> dict:
    """Write Earn `low` picks 2-10 from EASY_EARN_LOW. pick_1 stays lattice.

    Off / buy / classic / medium / high are not touched. Also patches the
    web `keno-paytables.json` so the HUD matches the math file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_low = doc["risks"]["low"]
    tables: dict[str, list[float]] = {"1": list(pick_one_row_earn("low"))}
    rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for k in PICKS:
        name = f"low_pick_{k}_earn"
        if k == 1:
            table, errors = list(tables["1"]), []
        else:
            table, errors = list(EASY_EARN_LOW[k]), []
        stats = mode_stats_for("low", k, table, True, False, False, 1.0, None)
        fails = list(errors) + check_gates(
            k, stats, earn=True, cost=1.0, risk="low"
        )
        off_top = max(off_low[str(k)])
        settled_top = stats["max_m"]
        advertised_top = max(table)
        if k >= 6 and advertised_top + 1e-9 < off_top:
            fails.append(
                f"advertised top {advertised_top:.1f}x < Off {off_top:.1f}x"
            )
        if settled_top + 1e-9 < off_top:
            fails.append(
                f"settled How-to {settled_top:.1f}x < Off {off_top:.1f}x"
            )
        if fails:
            failures[name] = fails
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"adv={advertised_top:7.1f} settled={settled_top:7.1f} "
            f"off={off_top:7.1f} hr={stats['hit_rate']:.4f} "
            f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
        )
        print(f"{'':20s} {table}")
    if failures:
        raise SystemExit(f"earn low gate failures: {failures}")
    doc["earn"]["low"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["earn"]["low"] = tables
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} earn.low")
    print(
        f"wrote {path} earn.low "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f}); "
        f"pick_1={tables['1']}"
    )
    return tables


def buy_chip_contract_gates(
    risk: str, k: int, buy: str, cost: float, placed: bool
) -> list[str]:
    """The three promises a buy chip sells, checked on the solved mode.

    1. Lumen pays the chip's cost multiple (`BUY_LUMEN_BOOST`), not the Earn ×2
       — priced into the coefficients, so the boost must equal the cost.
    2. Every pick size places the star on a pick (`placed`). Catch is
       hit-or-miss (P=0.25); a full card always catches. Hit pays the chip
       boost, miss leaves the base row.
    3. The two extras are what the purchase buys: they open unconditionally
       with reason `bought` on every book.
    """
    f: list[str] = []
    boost = lumen_boost_for(risk, buy)
    if boost != cost:
        f.append(f"Lumen boost {boost:g}x != chip cost {cost:g}x")
    contract = buy in BUY_COSTS
    if contract and not placed:
        f.append(
            f"pick {k} solved without the placed-on-pick Lumen the chip sells"
        )
    if placed:
        outcomes = spin_outcomes(k, paying=None, bought=True, placed=True)
        if not any(s.lumen_hit for s in outcomes) or not any(
            not s.lumen_hit for s in outcomes
        ):
            f.append("placed Lumen did not book both a catch and a miss")
        full = [s for s in outcomes if s.main_hits == k]
        if full and any(not s.lumen_hit for s in full):
            f.append("full card missed the marked pick")
        unbought = [s for s in outcomes if not s.extras or s.extra_reason != "bought"]
        if unbought:
            f.append(f"{len(unbought)} of {len(outcomes)} books without forced extras")
    return f


def patch_buy_low(paytables_path: str | None = None) -> dict:
    """Re-solve Buy low 10x/100x only. Tops from easy_buy_low.JSON_MAX_LADDER."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_low = doc["risks"]["low"]
    earn_low = doc["earn"]["low"]
    failures: dict[str, list[str]] = {}
    out: dict[str, dict[str, list[float]]] = {}
    all_rtps: list[float] = []
    for buy, cost in BUY_COSTS.items():
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            name = f"low_pick_{k}_{buy}"
            placed = lumen_placed_on_pick(buy, k)
            if k == 1:
                # Chip-specific lattice. Lumen sits on the only pick (hit-or-miss).
                baked = EASY_BUY_LOW_PICK1.get(buy)
                if baked is not None:
                    table, errors = [m / cost for m in baked], []
                else:
                    table, errors = buy_pick_one_row("low", cost, buy)
            elif k in EASY_BUY_LOW:
                # Easy buy leftover-share / lock-clean chart (easy_buy_low.py).
                table, errors = easy_buy_cost_row(k, buy), []
            else:
                pinned = scaled_row_for(buy, "low", k, cost)
                if pinned is not None:
                    table, errors = [m / cost for m in pinned], []
                else:
                    table, errors = solve_table(
                        "low", k, True, True, cost, placed, buy
                    )
            stats = mode_stats_for(
                "low", k, table, True, True, placed, cost, buy
            )
            fails = list(errors) + check_gates(
                k, stats, earn=True, cost=cost, risk="low"
            ) + buy_chip_contract_gates("low", k, buy, cost, placed)
            json_top = round(max(table) * cost, 1)
            off_top = max(off_low[str(k)])
            earn_how_to = max(earn_low[str(k)]) * 4.0
            vs_debit = stats["max_m"]
            # Buy low may exceed Off Easy max on picks 5–10 (priced under
            # placed Lumen + Pulse). Still must not raise Earn How-to on
            # picks 8–10. pick_1 is the buy lattice, not a jackpot.
            if k >= 8 and vs_debit - earn_how_to > 1e-9:
                fails.append(
                    f"vs-debit {vs_debit:.1f}x raises Earn How-to {earn_how_to:.1f}x"
                )
            if fails:
                failures[name] = fails
            tables[str(k)] = [round(m * cost, 1) for m in table]
            all_rtps.append(stats["rtp"])
            print(
                f"{name:22s} rtp={stats['rtp']:.4f} json={json_top:7.1f} "
                f"vs_debit={vs_debit:7.1f} off={off_top:6.1f} "
                f"earn_how={earn_how_to:7.1f} hr={stats['hit_rate']:.4f} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':22s} {tables[str(k)]}")
        out[buy] = tables
    # HUD maxes must not fall as the card deepens (pick 3 under pick 2 is the
    # inversion the restairs removed). The chain starts at pick 2: pick_1 is
    # the buy lattice, not a jackpot, and its single hit cell (16.7x JSON)
    # towers over every deep-card top by design. Audited on buy10; buy100 low
    # still carries its own inversion pending the same probe on 100x Lumen.
    tables = out["buy10"]
    prev_k, prev_top = 2, max(tables["2"])
    for k in PICKS[2:]:
        top = max(tables[str(k)])
        if top + 1e-9 < prev_top:
            failures.setdefault(f"low_pick_{k}_buy10", []).append(
                f"JSON top {top:.1f}x < pick {prev_k} {prev_top:.1f}x "
                "(HUD maxes must climb with pick count)"
            )
        prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"buy low gate failures: {failures}")
    for buy, tables in out.items():
        doc[buy]["low"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} buy10/buy100.low "
        f"({len(all_rtps)} modes, rtp {min(all_rtps):.4f}-{max(all_rtps):.4f})"
    )
    return out





def patch_buy_classic(paytables_path: str | None = None) -> dict:
    """Re-solve Buy classic 10x/100x only. Tops from easy_buy_classic.JSON_MAX_LADDER."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_classic = doc["risks"]["classic"]
    earn_classic = doc["earn"]["classic"]
    failures: dict[str, list[str]] = {}
    out: dict[str, dict[str, list[float]]] = {}
    all_rtps: list[float] = []
    for buy, cost in BUY_COSTS.items():
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            name = f"classic_pick_{k}_{buy}"
            placed = lumen_placed_on_pick(buy, k)
            if k == 1:
                baked = EASY_BUY_CLASSIC_PICK1.get(buy)
                if baked is not None:
                    table, errors = [m / cost for m in baked], []
                else:
                    table, errors = buy_pick_one_row("classic", cost, buy)
            elif k in EASY_BUY_CLASSIC:
                table, errors = easy_buy_classic_cost_row(k, buy), []
            else:
                table, errors = solve_table(
                    "classic", k, True, True, cost, placed, buy
                )
            stats = mode_stats_for(
                "classic", k, table, True, True, placed, cost, buy
            )
            fails = list(errors) + check_gates(
                k, stats, earn=True, cost=cost, risk="classic"
            ) + buy_chip_contract_gates("classic", k, buy, cost, placed)
            json_top = round(max(table) * cost, 1)
            off_top = max(off_classic[str(k)])
            earn_how_to = max(earn_classic[str(k)]) * 4.0
            vs_debit = stats["max_m"]
            # Buy classic may exceed Off classic max on picks 6–10 (priced under
            # placed Lumen + Pulse). Still must not raise Earn How-to on
            # picks 8–10. pick_1 is the buy lattice, not a jackpot.
            if k >= 8 and vs_debit - earn_how_to > 1e-9:
                fails.append(
                    f"vs-debit {vs_debit:.1f}x raises Earn How-to {earn_how_to:.1f}x"
                )
            if fails:
                failures[name] = fails
            tables[str(k)] = [round(m * cost, 1) for m in table]
            all_rtps.append(stats["rtp"])
            print(
                f"{name:22s} rtp={stats['rtp']:.4f} json={json_top:7.1f} "
                f"vs_debit={vs_debit:7.1f} off={off_top:6.1f} "
                f"earn_how={earn_how_to:7.1f} hr={stats['hit_rate']:.4f} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':22s} {tables[str(k)]}")
        out[buy] = tables
    # HUD maxes must not fall as the card deepens (from pick 2). Audited on buy10.
    tables = out["buy10"]
    prev_k, prev_top = 2, max(tables["2"])
    for k in PICKS[2:]:
        top = max(tables[str(k)])
        if top + 1e-9 < prev_top:
            failures.setdefault(f"classic_pick_{k}_buy10", []).append(
                f"JSON top {top:.1f}x < pick {prev_k} {prev_top:.1f}x "
                "(HUD maxes must climb with pick count)"
            )
        prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"buy classic gate failures: {failures}")
    for buy, tables in out.items():
        doc[buy]["classic"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} buy10/buy100.classic "
        f"({len(all_rtps)} modes, rtp {min(all_rtps):.4f}-{max(all_rtps):.4f})"
    )
    return out




def patch_buy_high(paytables_path: str | None = None) -> dict:
    """Re-solve Buy high 10x/100x. Tops from easy_buy_high ladders."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_high = doc["risks"]["high"]
    earn_high = doc["earn"]["high"]
    failures: dict[str, list[str]] = {}
    out: dict[str, dict[str, list[float]]] = {}
    all_rtps: list[float] = []
    for buy, cost in BUY_COSTS.items():
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            name = f"high_pick_{k}_{buy}"
            placed = lumen_placed_on_pick(buy, k)
            if k == 1:
                baked = EASY_BUY_HIGH_PICK1.get(buy)
                table, errors = [m / cost for m in baked], []
            else:
                table, errors = easy_buy_high_cost_row(k, buy), []
            stats = mode_stats_for("high", k, table, True, True, placed, cost, buy)
            fails = list(errors) + check_gates(
                k, stats, earn=True, cost=cost, risk="high"
            ) + buy_chip_contract_gates("high", k, buy, cost, placed)
            json_top = round(max(table) * cost, 1)
            off_top = max(off_high[str(k)])
            earn_how_to = max(earn_high[str(k)]) * 4.0
            vs_debit = stats["max_m"]
            if k >= 8 and vs_debit - earn_how_to > 1e-9:
                fails.append(
                    f"vs-debit {vs_debit:.1f}x raises Earn How-to {earn_how_to:.1f}x"
                )
            if fails:
                failures[name] = fails
            tables[str(k)] = [round(m * cost, 1) for m in table]
            all_rtps.append(stats["rtp"])
            print(
                f"{name:22s} rtp={stats['rtp']:.4f} json={json_top:7.1f} "
                f"vs_debit={vs_debit:7.1f} off={off_top:6.1f} "
                f"earn_how={earn_how_to:7.1f} hr={stats['hit_rate']:.4f} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':22s} {tables[str(k)]}")
        out[buy] = tables
        # HUD climb from pick 2
        prev_k, prev_top = 2, max(tables["2"])
        for k in PICKS[2:]:
            top = max(tables[str(k)])
            if top + 1e-9 < prev_top:
                failures.setdefault(f"high_pick_{k}_{buy}", []).append(
                    f"JSON top {top:.1f}x < pick {prev_k} {prev_top:.1f}x "
                    "(HUD maxes must climb with pick count)"
                )
            prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"buy high gate failures: {failures}")
    for buy, tables in out.items():
        doc[buy]["high"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} buy10/buy100.high "
        f"({len(all_rtps)} modes, rtp {min(all_rtps):.4f}-{max(all_rtps):.4f})"
    )
    return out


def patch_buy_medium(paytables_path: str | None = None) -> dict:
    """Re-solve Buy medium 10x/100x. Tops from easy_buy_medium ladders."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_medium = doc["risks"]["medium"]
    earn_medium = doc["earn"]["medium"]
    failures: dict[str, list[str]] = {}
    out: dict[str, dict[str, list[float]]] = {}
    all_rtps: list[float] = []
    for buy, cost in BUY_COSTS.items():
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            name = f"medium_pick_{k}_{buy}"
            placed = lumen_placed_on_pick(buy, k)
            if k == 1:
                baked = EASY_BUY_MEDIUM_PICK1.get(buy)
                table, errors = [m / cost for m in baked], []
            else:
                table, errors = easy_buy_medium_cost_row(k, buy), []
            stats = mode_stats_for(
                "medium", k, table, True, True, placed, cost, buy
            )
            fails = list(errors) + check_gates(
                k, stats, earn=True, cost=cost, risk="medium"
            ) + buy_chip_contract_gates("medium", k, buy, cost, placed)
            json_top = round(max(table) * cost, 1)
            off_top = max(off_medium[str(k)])
            earn_how_to = max(earn_medium[str(k)]) * 4.0
            vs_debit = stats["max_m"]
            if k >= 8 and vs_debit - earn_how_to > 1e-9:
                fails.append(
                    f"vs-debit {vs_debit:.1f}x raises Earn How-to {earn_how_to:.1f}x"
                )
            if fails:
                failures[name] = fails
            tables[str(k)] = [round(m * cost, 1) for m in table]
            all_rtps.append(stats["rtp"])
            print(
                f"{name:22s} rtp={stats['rtp']:.4f} json={json_top:7.1f} "
                f"vs_debit={vs_debit:7.1f} off={off_top:6.1f} "
                f"earn_how={earn_how_to:7.1f} hr={stats['hit_rate']:.4f} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':22s} {tables[str(k)]}")
        out[buy] = tables
        prev_k, prev_top = 2, max(tables["2"])
        for k in PICKS[2:]:
            top = max(tables[str(k)])
            if top + 1e-9 < prev_top:
                failures.setdefault(f"medium_pick_{k}_{buy}", []).append(
                    f"JSON top {top:.1f}x < pick {prev_k} {prev_top:.1f}x "
                    "(HUD maxes must climb with pick count)"
                )
            prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"buy medium gate failures: {failures}")
    for buy, tables in out.items():
        doc[buy]["medium"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} buy10/buy100.medium "
        f"({len(all_rtps)} modes, rtp {min(all_rtps):.4f}-{max(all_rtps):.4f})"
    )
    return out



def patch_earn_medium(paytables_path: str | None = None) -> dict:
    """Re-solve Earn `medium` only. Off medium and every other ladder stay put."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_medium = doc["risks"]["medium"]
    tables: dict[str, list[float]] = {}
    rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for k in PICKS:
        name = f"medium_pick_{k}_earn"
        if k == 1:
            table, errors = pick_one_row_earn("medium"), []
        else:
            table, errors = solve_table("medium", k, True, False, 1.0, False, None)
        stats = mode_stats_for("medium", k, table, True, False, False, 1.0, None)
        fails = list(errors) + check_gates(
            k, stats, earn=True, cost=1.0, risk="medium"
        )
        off_top = max(off_medium[str(k)])
        settled_top = stats["max_m"]
        advertised_top = max(table)
        # Advertised may sit under Off (Lumen x2 x Pulse x2). How-to vs Off
        # is the identity; pinning advertised >= Off is what built the
        # 2.6 -> 406 / 29.9 -> 650 / 225 -> 5000 cliffs.
        if settled_top + 1e-9 < off_top:
            fails.append(
                f"settled How-to {settled_top:.1f}x < Off {off_top:.1f}x"
            )
        if fails:
            failures[name] = fails
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"adv={advertised_top:7.1f} settled={settled_top:7.1f} "
            f"off={off_top:7.1f} hr={stats['hit_rate']:.4f} "
            f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
        )
        print(f"{'':20s} {table}")
    prev_k, prev_top = None, None
    for k in PICKS:
        top = max(tables[str(k)])
        if prev_top is not None and top + 1e-9 < prev_top:
            failures.setdefault(f"medium_pick_{k}_earn", []).append(
                f"advertised max {top:g}x < pick {prev_k} {prev_top:g}x "
                "(HUD 8/8 < 9/9 < 10/10 must climb)"
            )
        prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"earn medium gate failures: {failures}")
    doc["earn"]["medium"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["earn"]["medium"] = tables
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} earn.medium")
    print(
        f"wrote {path} earn.medium "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f})"
    )
    return tables



def patch_earn_high(paytables_path: str | None = None) -> dict:
    """Re-solve Earn `high` only. Off high and every other ladder stay put."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_high = doc["risks"]["high"]
    tables: dict[str, list[float]] = {}
    rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for k in PICKS:
        name = f"high_pick_{k}_earn"
        pinned = scaled_row_for("earn", "high", k)
        if k == 1:
            table, errors = pick_one_row_earn("high"), []
        elif pinned is not None:
            # Restaired by hand and held under the shape lock; re-solving it
            # would re-pack the body cells the restair spread out.
            table, errors = pinned, []
        else:
            table, errors = solve_table("high", k, True, False, 1.0, False, None)
        stats = mode_stats_for("high", k, table, True, False, False, 1.0, None)
        fails = list(errors) + check_gates(
            k, stats, earn=True, cost=1.0, risk="high"
        )
        off_top = max(off_high[str(k)])
        settled_top = stats["max_m"]
        advertised_top = max(table)
        # k>=9 advertised >= 25000 would be flat; 9 pins 12500 so the HUD
        # climbs 6100 < 12500 < 25000. k=8 pins to Off 6100 (std envelope).
        # k=5-7 advertised under Off, How-to >= Off. k=2-4 lattice under Off
        # advertised; How-to >= Off.
        if k >= 9:
            pin_floor = min(off_top, 25000.0)
            if k == 9:
                pin_floor = HIGH_EARN_TOP[9]
            if advertised_top + 1e-9 < pin_floor:
                fails.append(
                    f"advertised top {advertised_top:.1f}x < pin {pin_floor:.1f}x"
                )
        if k != 5 and settled_top + 1e-9 < off_top:
            fails.append(
                f"settled How-to {settled_top:.1f}x < Off {off_top:.1f}x"
            )
        if fails:
            failures[name] = fails
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"adv={advertised_top:7.1f} settled={settled_top:7.1f} "
            f"off={off_top:7.1f} hr={stats['hit_rate']:.4f} "
            f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
        )
        print(f"{'':20s} {table}")
    prev_k, prev_top = None, None
    for k in PICKS:
        top = max(tables[str(k)])
        if prev_top is not None and top + 1e-9 < prev_top:
            failures.setdefault(f"high_pick_{k}_earn", []).append(
                f"advertised max {top:g}x < pick {prev_k} {prev_top:g}x "
                "(HUD maxes must climb with pick count)"
            )
        prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"earn high gate failures: {failures}")
    doc["earn"]["high"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} earn.high "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f})"
    )
    return tables


def patch_earn_classic(paytables_path: str | None = None) -> dict:
    """Re-solve Earn `classic` only. Off classic and every other ladder stay put."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    off_classic = doc["risks"]["classic"]
    tables: dict[str, list[float]] = {}
    rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for k in PICKS:
        name = f"classic_pick_{k}_earn"
        pinned = scaled_row_for("earn", "classic", k)
        if k == 1:
            table, errors = pick_one_row_earn("classic"), []
        elif pinned is not None:
            # Restaired by hand and held under the shape lock; re-solving it
            # would re-pack the body cells the restair spread out.
            table, errors = pinned, []
        else:
            table, errors = solve_table("classic", k, True, False, 1.0, False, None)
        stats = mode_stats_for("classic", k, table, True, False, False, 1.0, None)
        fails = list(errors) + check_gates(
            k, stats, earn=True, cost=1.0, risk="classic"
        )
        off_top = max(off_classic[str(k)])
        settled_top = stats["max_m"]
        advertised_top = max(table)
        # Advertised may sit under Off (Lumen x2 x Pulse x2). How-to vs Off
        # is the identity; pinning advertised >= Off packed pick 6 as 9.9 -> 200.
        if settled_top + 1e-9 < off_top:
            fails.append(
                f"settled How-to {settled_top:.1f}x < Off {off_top:.1f}x"
            )
        if fails:
            failures[name] = fails
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"adv={advertised_top:7.1f} settled={settled_top:7.1f} "
            f"off={off_top:7.1f} hr={stats['hit_rate']:.4f} "
            f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
        )
        print(f"{'':20s} {table}")
    prev_k, prev_top = None, None
    for k in PICKS:
        top = max(tables[str(k)])
        if prev_top is not None and top + 1e-9 < prev_top:
            failures.setdefault(f"classic_pick_{k}_earn", []).append(
                f"advertised max {top:g}x < pick {prev_k} {prev_top:g}x "
                "(HUD maxes must climb with pick count)"
            )
        prev_k, prev_top = k, top
    if failures:
        raise SystemExit(f"earn classic gate failures: {failures}")
    doc["earn"]["classic"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(
        f"wrote {path} earn.classic "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f})"
    )
    return tables




def patch_off_high(paytables_path: str | None = None) -> dict:
    """Write Off `high` picks 2-10 from HIGH_OFF. pick_1 stays lattice.

    Earn / buy / classic / low / medium are not touched. Also patches the
    web `keno-paytables.json` so the HUD matches the math file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    tables: dict[str, list[float]] = dict(doc["risks"]["high"])
    tables["1"] = list(pick_one_row("high"))
    pick1_stats = base_stats(1, tables["1"], "high")
    print(
        f"{'high_pick_1':20s} rtp={pick1_stats['rtp']:.4f} "
        f"std={pick1_stats['std']:6.2f} max={pick1_stats['max_m']:8.1f} "
        f"hr={pick1_stats['hit_rate']:.4f} (lattice + miss-bonus third tier)"
    )
    print(f"{'':20s} {tables['1']}")
    rtps: list[float] = []
    for k in range(2, 11):
        name = f"high_pick_{k}"
        table = list(HIGH_OFF[k])
        stats = base_stats(k, table)
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
            f"etl40={stats['etl40']:.3f} cvar={stats['cvar']:6.1f} "
            f"etl_sum={stats['etl_sum']:.3f} ok"
        )
        print(f"{'':20s} {table}")
    doc["risks"]["high"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["risks"]["high"] = tables
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} risks.high")
    print(
        f"wrote {path} risks.high "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f}); "
        f"pick_1={tables['1']}"
    )
    return tables


def patch_off_medium(paytables_path: str | None = None) -> dict:
    """Write Off `medium` picks 2-10 from MEDIUM_OFF. pick_1 stays lattice.

    Earn / buy / classic / low / high are not touched. Also patches the
    web `keno-paytables.json` so the HUD matches the math file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    tables: dict[str, list[float]] = dict(doc["risks"]["medium"])
    tables["1"] = list(pick_one_row("medium"))
    pick1_stats = base_stats(1, tables["1"], "medium")
    print(
        f"{'medium_pick_1':20s} rtp={pick1_stats['rtp']:.4f} "
        f"std={pick1_stats['std']:6.2f} max={pick1_stats['max_m']:8.1f} "
        f"hr={pick1_stats['hit_rate']:.4f} (lattice + miss-bonus third tier)"
    )
    print(f"{'':20s} {tables['1']}")
    rtps: list[float] = []
    for k in range(2, 11):
        name = f"medium_pick_{k}"
        table = list(MEDIUM_OFF[k])
        stats = base_stats(k, table)
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
            f"etl40={stats['etl40']:.3f} etl_sum={stats['etl_sum']:.3f} ok"
        )
        print(f"{'':20s} {table}")
    doc["risks"]["medium"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["risks"]["medium"] = tables
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} risks.medium")
    print(
        f"wrote {path} risks.medium "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f}); "
        f"pick_1={tables['1']}"
    )
    return tables


def patch_off_low(paytables_path: str | None = None) -> dict:
    """Write Off `low` picks 2-10 from EASY_OFF_LOW. pick_1 stays lattice.

    Earn / buy / classic / medium / high are not touched. Also patches the
    web `keno-paytables.json` so the HUD matches the math file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    tables: dict[str, list[float]] = dict(doc["risks"]["low"])
    tables["1"] = list(pick_one_row("low"))
    rtps: list[float] = []
    for k in range(2, 11):
        name = f"low_pick_{k}"
        table = list(EASY_OFF_LOW[k])
        stats = base_stats(k, table)
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
            f"etl_sum={stats['etl_sum']:.3f} ok"
        )
        print(f"{'':20s} {table}")
    doc["risks"]["low"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["risks"]["low"] = tables
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} risks.low")
    print(
        f"wrote {path} risks.low "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f}); "
        f"pick_1={tables['1']}"
    )
    return tables


def patch_off_classic(paytables_path: str | None = None) -> dict:
    """Write Off `classic` picks 2-10 from CLASSIC_OFF. pick_1 stays lattice.

    Earn / buy / low / medium / high are not touched. Also patches the
    web `keno-paytables.json` so the HUD matches the math file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    tables: dict[str, list[float]] = dict(doc["risks"]["classic"])
    tables["1"] = list(pick_one_row("classic"))
    pick1_stats = base_stats(1, tables["1"], "classic")
    print(
        f"{'classic_pick_1':20s} rtp={pick1_stats['rtp']:.4f} "
        f"std={pick1_stats['std']:6.2f} max={pick1_stats['max_m']:8.1f} "
        f"hr={pick1_stats['hit_rate']:.4f} (lattice + 1-in-5 miss bonus)"
    )
    print(f"{'':20s} {tables['1']}")
    doc["pick1Bonus"] = {
        "weight": PICK_ONE_BONUS_WEIGHT,
        "missWeight": MISS_WEIGHT,
        "total": MISS_WEIGHT + HIT_WEIGHT,
        "pay": {
            risk: pick_one_bonus_miss(risk) for risk in sorted(PICK_ONE_BONUS_RISKS)
        },
    }
    rtps: list[float] = []
    for k in range(2, 11):
        name = f"classic_pick_{k}"
        table = list(CLASSIC_OFF[k])
        stats = base_stats(k, table)
        tables[str(k)] = table
        rtps.append(stats["rtp"])
        print(
            f"{name:20s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
            f"etl_sum={stats['etl_sum']:.3f} ok"
        )
        print(f"{'':20s} {table}")
    doc["risks"]["classic"] = tables
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        web["risks"]["classic"] = tables
        web["pick1Bonus"] = doc["pick1Bonus"]
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} risks.classic")
    print(
        f"wrote {path} risks.classic "
        f"({len(rtps)} modes, rtp {min(rtps):.4f}-{max(rtps):.4f}); "
        f"pick_1={tables['1']}"
    )
    return tables


def patch_earn_pick_one(paytables_path: str | None = None) -> dict:
    """Rewrite Earn + buy pick_1 only. Picks 2–10 keep their Pulse 10% ladders.

    Pulse chance on one pick is per-risk so advertised hits follow Off's miss
    ladder (low 2.1 < classic 2.4 < medium 2.9 < high 3.2) inside MODE_RTP_BAND.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = paytables_path or os.path.join(here, "paytables.json")
    with open(path, encoding="UTF-8") as handle:
        doc = json.load(handle)
    failures: dict[str, list[str]] = {}
    earn_rows: dict[str, list[float]] = {}
    for risk in ("low", "classic", "medium", "high"):
        table = list(pick_one_row_earn(risk))
        stats = mode_stats_for(risk, 1, table, True, False, False, 1.0, None)
        fails = check_gates(1, stats, earn=True, cost=1.0, risk=risk)
        name = f"{risk}_pick_1_earn"
        if fails:
            failures[name] = fails
        earn_rows[risk] = table
        doc["earn"][risk]["1"] = table
        print(
            f"{name:22s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
            f"adv={table} settled={stats['max_m']:.1f} "
            f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
        )
    hits = [earn_rows[r][1] for r in ("low", "classic", "medium", "high")]
    if hits != sorted(hits) or len(set(hits)) < 4:
        failures["hierarchy"] = [f"Earn pick_1 hits {hits} are not strictly increasing"]
    buy_rows: dict[str, dict[str, list[float]]] = {}
    for buy, cost in BUY_COSTS.items():
        buy_rows[buy] = {}
        for risk in ("low", "classic", "medium", "high"):
            table, errors = buy_pick_one_row(risk, cost, buy)
            stats = mode_stats_for(
                risk, 1, table, True, True, False, cost, buy
            )
            fails = list(errors) + check_gates(
                1, stats, earn=True, cost=cost, risk=risk
            )
            json_row = [round(m * cost, 1) for m in table]
            name = f"{risk}_pick_1_{buy}"
            if fails:
                failures[name] = fails
            buy_rows[buy][risk] = json_row
            doc[buy][risk]["1"] = json_row
            print(
                f"{name:22s} rtp={stats['rtp']:.4f} json={json_row} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
    if failures:
        raise SystemExit(f"earn pick_1 gate failures: {failures}")
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    web_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    if os.path.isfile(web_path):
        with open(web_path, encoding="UTF-8") as handle:
            web = json.load(handle)
        for risk, table in earn_rows.items():
            web["earn"][risk]["1"] = table
        for buy, rows in buy_rows.items():
            for risk, table in rows.items():
                web[buy][risk]["1"] = table
        with open(web_path, "w", encoding="UTF-8") as handle:
            json.dump(web, handle, indent=2)
            handle.write("\n")
        print(f"wrote {web_path} earn/buy pick_1")
    print(f"wrote {path} earn/buy pick_1 hits={hits}")
    return earn_rows


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--earn-low":
        patch_earn_low()
    elif len(sys.argv) > 1 and sys.argv[1] == "--earn-pick-one":
        patch_earn_pick_one()
    elif len(sys.argv) > 1 and sys.argv[1] == "--off-low":
        patch_off_low()
    elif len(sys.argv) > 1 and sys.argv[1] == "--off-classic":
        patch_off_classic()
    elif len(sys.argv) > 1 and sys.argv[1] == "--earn-classic":
        patch_earn_classic()
    elif len(sys.argv) > 1 and sys.argv[1] == "--buy-classic":
        patch_buy_classic()
    elif len(sys.argv) > 1 and sys.argv[1] == "--buy-medium":
        patch_buy_medium()
    elif len(sys.argv) > 1 and sys.argv[1] == "--off-medium":
        patch_off_medium()
    elif len(sys.argv) > 1 and sys.argv[1] == "--off-high":
        patch_off_high()
    elif len(sys.argv) > 1 and sys.argv[1] == "--earn-medium":
        patch_earn_medium()
    elif len(sys.argv) > 1 and sys.argv[1] == "--earn-high":
        patch_earn_high()
    elif len(sys.argv) > 1 and sys.argv[1] == "--buy-high":
        patch_buy_high()
    elif len(sys.argv) > 1 and sys.argv[1] == "--buy-low":
        patch_buy_low()
    elif len(sys.argv) > 1 and sys.argv[1] == "--buy-100":
        # All four risks' buy100 (and buy10 where those patches own both chips).
        patch_buy_classic()
        patch_buy_low()
        patch_buy_medium()
        patch_buy_high()
    else:
        off, off_rtps = solve_off()
        earn, earn_rtps = solve_earn()
        buys, buy_rtps = solve_buy()
        # Buy RTP is per cost, so it belongs in the same spread check as the rest:
        # a player choosing between Earn and a buy chip is choosing between returns
        # on the money they are about to spend either way.
        check_spread(off_rtps + earn_rtps + buy_rtps)
        write_outputs(off, earn, buys)
