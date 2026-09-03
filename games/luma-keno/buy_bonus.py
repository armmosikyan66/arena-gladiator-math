"""Shared buy-bonus ladder solver for every risk × buy10/buy100.

Buy settlement (all risks):
  • extras forced open (`bought`) on every book
  • every pick size: Lumen *placed* on a pick (`lumen_placed_on_pick`);
    catch is hit-or-miss on the ten (P=0.25, P(hit|h)=h/k). Extras that
    cover every remaining pick (pick_1 extra catch) also pay BUY_LUMEN_BOOST.
    (10× / 100×) on a paying row; miss leaves the base. Full card always
    catches. pick_1 is included (not forced into the ten, so STD survives)
  • Pulse ×2 on extra-open books (10% on picks 2–10; pick_1 uses the Earn
    per-risk slice except buy100 pick_1, which nudges classic 7% / medium 13%
    so extra-cover 0.30 catch still has an in-band 0.1× pair)

Advertised rows live in **base-bet / JSON units**. The solve grades them in
cost units (`json / cost`). Because BUY_LUMEN_BOOST equals the chip cost,
one JSON chart often serves both buy10 and buy100 for picks 2–10 (low);
classic deep buy100 floors tops via the Max Payout pin. Medium/high buy100
ships a separate JSON_MAX ladder + baked bodies (100× Lumen cannot fund
buy10 deep tops without cliffs / illegal RTP).

Algorithm (picks 2–10)
----------------------
1. Lock JSON top from `BuyRiskConfig.json_max_ladder` (optionally floored by
   the chip Max Payout pin when `apply_payout_cap`).
2. Keep the designed `zero_mask`.
3. Seed from geometric body and/or HUD share leftover and/or adapted baked
   row (config knobs).
4. Hill-climb body cells; score legal → gradual max-step → RTP closeness.
5. Reject rows outside MODE_RTP_BAND / RTP_WINDOW / hit-rate / ETL /
   buy-chip contract / shape_lock.

Risk plug-in
------------
Build a `BuyRiskConfig` (see `easy_buy_low` / `easy_buy_classic`) and call
`retarget_buy_row` / `generate_buy_chart`. Medium/high register via `easy_buy_medium` / `easy_buy_high`;
`risk_stub` lazy-imports every risk config.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from keno_pick_one import (
    MODE_RTP_BAND,
    RTP_TARGET,
    effective_coeff,
    lumen_placed_on_pick,
    settled_stats,
)
from shape_lock import lock_for, solve_row, violations

#: Designed window around 0.9650, inside MODE_RTP_BAND.
RTP_WINDOW = (0.9630, 0.9655)

_TARGET = Fraction(str(RTP_TARGET))

BUY_COSTS = {"buy10": 10.0, "buy100": 100.0}

#: Dashboard Max Payout Multiplier (base-bet). vs-debit ≈ Pulse×JSON with
#: placed Lumen (boost == cost), so JSON ≤ MAX_PAYOUT_ABS[cost] / (2 × cost).
#: 2026-09-03 headline parity: buy chips pin at 100_000 on `high` pick 10 —
#: JSON 5,000 (buy10) / 500 (buy100), both settling 100,000x the base bet at
#: the 3-Star ceiling exactly. The old 10% margin rule is dropped for this one
#: pin: Off/Earn already sit on the same 100,000x boundary, and `rgs_verification`
#: gates max_win at 100_000*100 cents with a strict `>`, so equality passes.
MAX_PAYOUT_ABS = {10.0: 100_000.0, 100.0: 100_000.0}


@dataclass(frozen=True)
class BuyRiskConfig:
    """Risk-specific knobs for the shared buy-bonus solver.

    Required for a full solve:
      risk, json_max_ladder, zero_mask, hud, baked (per chip).

    Optional hooks for medium/high (and classic payout pin):
      apply_payout_cap, use_geometric_seed, fix_last_catch_on_climb,
      neighbour_deltas / transfer_steps / climb_guards, pick1, off_chart,
      earn_how_to_cap, buy_bonus_min_pick.
    """

    risk: str
    json_max_ladder: Mapping[int, float]
    zero_mask: Mapping[int, tuple[bool, ...]]
    hud: Mapping[int, list[float]]
    #: Chip → pick → JSON row. Low ships one chart under both keys; classic
    #: has separate buy100 bodies when the payout pin binds.
    baked: Mapping[str, Mapping[int, list[float]]] = field(default_factory=dict)
    pick1: Mapping[str, list[float]] = field(default_factory=dict)
    off_chart: Mapping[int, list[float]] = field(default_factory=dict)
    #: Optional buy100-only JSON tops (medium/high deep picks under 100× Lumen).
    json_max_ladder_buy100: Mapping[int, float] | None = None
    #: Optional buy100-only zero-mask overrides (sparse; falls back to zero_mask).
    zero_mask_buy100: Mapping[int, tuple[bool, ...]] | None = None
    #: Floor designed tops by Max Payout (classic / future medium-high).
    apply_payout_cap: bool = False
    #: Prefer gradual geometric body seeds (needed for smooth low ladders).
    use_geometric_seed: bool = True
    #: On climb for k≥8, pin penultimate into shape_lock last_catch band.
    fix_last_catch_on_climb: bool = False
    neighbour_deltas: tuple[int, ...] = (-8, -5, -3, -2, -1, 1, 2, 3, 5, 8)
    transfer_steps: tuple[int, ...] = (1, 2, 3, 5, 8, 12)
    climb_guards: int = 100
    #: Prefer inserting the exact baked cost row when its top matches mx.
    prefer_exact_baked: bool = False
    #: Validation: picks ≥ this with ladder top > Off must clear Off (None=skip).
    buy_bonus_min_pick: int | None = None
    #: Validation: vs-debit How-to caps on deep picks (JSON How-to via stats).
    earn_how_to_cap: Mapping[int, float] = field(default_factory=dict)


def grid_step(cost: float) -> float:
    """One advertised tick in cost units (= 0.1× base bet)."""
    return round(0.1 / cost, 10)


def snap(value: float, cost: float) -> float:
    if value <= 0:
        return 0.0
    step = grid_step(cost)
    ticks = int(Fraction(str(value)) / Fraction(str(step)) + Fraction("1/2"))
    return round(ticks * step, 10)


def floor_snap(value: float, cost: float) -> float:
    if value <= 0:
        return 0.0
    step = grid_step(cost)
    ticks = int(Fraction(str(value)) / Fraction(str(step)) + Fraction("1/1000000"))
    return round(ticks * step, 10)


def floor_json_to_cost(json_top: float, cost: float) -> float:
    ticks = 10.0 * cost
    return math.floor(json_top / cost * ticks + 1e-9) / ticks


def to_json_row(cost_row: list[float], cost: float) -> list[float]:
    return [round(m * cost, 1) for m in cost_row]


def paying_from_mask(mask: tuple[bool, ...]) -> frozenset[int]:
    return frozenset(h for h, z in enumerate(mask) if not z)


def json_max_for(cfg: BuyRiskConfig, k: int, cost: float) -> float:
    """Designed JSON top, optionally floored by the chip's Max Payout pin."""
    if (
        abs(cost - 100.0) < 1e-12
        and cfg.json_max_ladder_buy100 is not None
        and k in cfg.json_max_ladder_buy100
    ):
        top = float(cfg.json_max_ladder_buy100[k])
    else:
        top = float(cfg.json_max_ladder[k])
    if cfg.apply_payout_cap:
        payout_json = MAX_PAYOUT_ABS[cost] / (2.0 * cost)
        top = min(top, payout_json)
    return top


def zero_mask_for(cfg: BuyRiskConfig, k: int, buy: str) -> tuple[bool, ...]:
    """Zero mask for this chip; buy100 may deepen zeros on deep picks."""
    if buy == "buy100" and cfg.zero_mask_buy100 and k in cfg.zero_mask_buy100:
        return cfg.zero_mask_buy100[k]
    return cfg.zero_mask[k]


def coeff_for(
    cfg: BuyRiskConfig, k: int, mask: tuple[bool, ...], buy: str
) -> tuple[float, ...]:
    placed = lumen_placed_on_pick(buy, k)
    return effective_coeff(
        cfg.risk, k, paying_from_mask(mask), bought=True, placed=placed, buy=buy
    )


def exact_rtp(coeff: tuple[float, ...], row: list[float]) -> Fraction:
    return sum(Fraction(str(c)) * Fraction(str(m)) for c, m in zip(coeff, row))


def shape_ok(
    k: int, mask: tuple[bool, ...], row: list[float], mx: float
) -> bool:
    if len(row) != k + 1 or abs(row[k] - mx) > 1e-12:
        return False
    if [m == 0 for m in row] != list(mask):
        return False
    paying = [m for m in row if m > 0]
    return all(b > a for a, b in zip(paying, paying[1:]))


def payout_capped(cfg: BuyRiskConfig, json_top: float, cost: float) -> bool:
    """True when the advertised top sits on the dashboard Max Payout pin."""
    if not cfg.apply_payout_cap:
        return False
    pin = MAX_PAYOUT_ABS[cost] / (2.0 * cost)
    return abs(json_top - pin) < 1e-6


def _exemption_covers(buy: str, risk: str, k: int, viol: list[str]) -> bool:
    try:
        from lock_exemptions import exemption_for
    except ImportError:
        return False
    ex = exemption_for(buy, risk, k)
    if ex is None:
        return False
    if "*" in ex.rules:
        return True
    tags = {
        "last-catch": "last_catch",
        "mid": "ratio_min_mid",
        "step": "ratio_max",
        "mega": "no_mega_jump",
    }
    for v in viol:
        covered = False
        for needle, rule in tags.items():
            if needle in v and rule in ex.rules:
                covered = True
                break
        if not covered:
            return False
    return True


def legal(
    cfg: BuyRiskConfig,
    k: int,
    mask: tuple[bool, ...],
    row: list[float],
    mx: float,
    cost: float,
    buy: str,
) -> bool:
    if not shape_ok(k, mask, row, mx):
        return False
    placed = lumen_placed_on_pick(buy, k)
    c = coeff_for(cfg, k, mask, buy)
    rtp = float(exact_rtp(c, row))
    lo, hi = MODE_RTP_BAND
    if not (lo < rtp < hi):
        return False
    if not (RTP_WINDOW[0] <= rtp <= RTP_WINDOW[1]):
        return False
    stats = settled_stats(
        cfg.risk, k, row, bought=True, placed=placed, cost=cost, buy=buy
    )
    if stats["hit_rate"] < 0.021 or stats["etl_sum"] > 1.45:
        return False
    capped = payout_capped(cfg, mx * cost, cost)
    viol = violations(row, k, lock=lock_for(cost, pick=k, capped=capped))
    if viol and not _exemption_covers(buy, cfg.risk, k, viol):
        return False
    return True


def max_step_ratio(row: list[float]) -> float:
    """Largest adjacent paying ratio — the cliff the HUD feels."""
    paying = [m for m in row if m > 0]
    if len(paying) < 2:
        return 0.0
    return max(b / a for a, b in zip(paying, paying[1:]))


def score(
    cfg: BuyRiskConfig,
    k: int,
    mask: tuple[bool, ...],
    row: list[float],
    mx: float,
    cost: float,
    buy: str,
) -> tuple:
    """Prefer legal rows, then gradual steps, then RTP closeness."""
    c = coeff_for(cfg, k, mask, buy)
    rtp = exact_rtp(c, row)
    legal_flag = 0 if legal(cfg, k, mask, row, mx, cost, buy) else 1
    return (legal_flag, max_step_ratio(row), abs(rtp - _TARGET))


def seed_from_shares(
    cfg: BuyRiskConfig,
    k: int,
    mask: tuple[bool, ...],
    mx: float,
    cost: float,
    buy: str,
) -> list[float]:
    c = coeff_for(cfg, k, mask, buy)
    hud = cfg.hud[k]
    weights = [
        0.0
        if mask[h]
        else (hud[h] if h < len(hud) and hud[h] > 0 else 1.0)
        for h in range(k)
    ]
    leftover = float(_TARGET) - c[k] * mx
    wh = sum(c[h] * weights[h] for h in range(k) if weights[h] > 0)
    row = [0.0] * (k + 1)
    row[k] = mx
    if wh <= 0 or leftover <= 0:
        return row
    for h in range(k):
        if weights[h] == 0 or c[h] == 0:
            continue
        row[h] = snap(leftover * weights[h] / wh, cost)
    for h, z in enumerate(mask):
        if z:
            row[h] = 0.0
    paying = [h for h, z in enumerate(mask) if not z]
    step = grid_step(cost)
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + step, 10)
        if b == k and row[a] >= mx:
            row[a] = round(mx - step, 10)
    return row


def seed_geometric(
    cfg: BuyRiskConfig,
    k: int,
    mask: tuple[bool, ...],
    mx: float,
    cost: float,
    buy: str,
) -> list[float]:
    """Climb from a small first pay toward the top with ~3× mid steps.

    Share-leftover seeding packs early hits (huge placed-Lumen coeffs) and
    leaves a cliff into the jackpot. A geometric body is the gradual seed
    the hill-climb then walks into the RTP window.
    """
    del cfg, buy  # risk/buy unused: geometric shape is lattice + mask + mx
    paying = [h for h, z in enumerate(mask) if not z]
    row = [0.0] * (k + 1)
    row[k] = mx
    if len(paying) < 2:
        return row
    body = paying[:-1]
    step = grid_step(cost)
    n = len(body)
    first = step * (2 if k <= 4 else 1)
    target_pen = max(first * (3.0 ** (n - 1)), mx / 5.0)
    if target_pen >= mx:
        target_pen = mx - step
    if n == 1:
        row[body[0]] = snap(min(target_pen, mx - step), cost)
        return row
    r = (target_pen / first) ** (1.0 / (n - 1)) if n > 1 else 3.0
    r = min(max(r, 1.5), 6.0)
    v = first
    for i, h in enumerate(body):
        if i:
            v *= r
        row[h] = snap(min(v, mx - step * (len(body) - i)), cost)
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + step, 10)
        if b == k and row[a] >= mx:
            row[a] = round(mx - step, 10)
    return row


def fix_last_catch(
    k: int,
    mask: tuple[bool, ...],
    row: list[float],
    mx: float,
    cost: float,
    *,
    capped: bool = False,
) -> list[float]:
    if k < 8 or capped:
        # Under the Max Payout pin the final catch is an ordinary step.
        return row
    lock = lock_for(cost, pick=k, capped=False)
    paying = [h for h, z in enumerate(mask) if not z]
    pen_h = paying[-2]
    pen = floor_snap(mx / lock.last_catch_min, cost)
    pen_lo = snap(mx / lock.last_catch_max, cost)
    if pen < pen_lo:
        pen = pen_lo
    row = list(row)
    row[pen_h] = pen
    row[k] = mx
    step = grid_step(cost)
    body = paying[:-2]
    if body and row[body[-1]] >= pen - 1e-12:
        factor = (pen - step) / max(row[body[-1]], step)
        for h in body:
            row[h] = snap(max(step, row[h] * factor), cost)
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + step, 10)
        if b == k and row[a] >= mx:
            row[a] = round(mx - step, 10)
    if mx / row[pen_h] < lock.last_catch_min - 1e-9:
        row[pen_h] = floor_snap(mx / lock.last_catch_min, cost)
    return row


def adapt_baked_seed(
    cfg: BuyRiskConfig, k: int, mx: float, cost: float, buy: str
) -> list[float] | None:
    """Prior baked row with the new top; deep picks also fix last_catch."""
    chart = cfg.baked.get(buy) or cfg.baked.get("buy10")
    if chart is None or k not in chart:
        return None
    mask = zero_mask_for(cfg, k, buy)
    row = [m / cost for m in chart[k]]
    row[k] = mx
    step = grid_step(cost)
    if k >= 8:
        capped = payout_capped(cfg, mx * cost, cost)
        if capped:
            return row
        if cfg.fix_last_catch_on_climb:
            row = fix_last_catch(k, mask, row, mx, cost, capped=False)
        else:
            # Low-style: reset penultimate into last_catch_min and scale body.
            lock = lock_for(cost, pick=k)
            paying = [h for h, z in enumerate(mask) if not z]
            pen_h = paying[-2]
            pen = snap(mx / lock.last_catch_min, cost)
            if mx / pen > lock.last_catch_max + 1e-9:
                pen = snap(mx / lock.last_catch_max, cost)
            row[pen_h] = pen
            body = paying[:-2]
            if body and row[body[-1]] >= pen - 1e-12:
                factor = (pen - step) / row[body[-1]]
                for h in body:
                    row[h] = snap(max(step, row[h] * factor), cost)
            for a, b in zip(paying, paying[1:]):
                if b != k and row[b] <= row[a]:
                    row[b] = round(row[a] + step, 10)
                if b == k and row[a] >= mx:
                    row[a] = round(mx - step, 10)
    return row


def neighbours(
    cfg: BuyRiskConfig, row: list[float], body: list[int], cost: float
) -> list[list[float]]:
    step = grid_step(cost)
    out: list[list[float]] = []
    for h in body:
        for delta in cfg.neighbour_deltas:
            trial = list(row)
            trial[h] = round(row[h] + delta * step, 10)
            if trial[h] > 0:
                out.append(trial)
        for h2 in body:
            if h2 == h:
                continue
            for steps in cfg.transfer_steps:
                trial = list(row)
                trial[h] = round(row[h] - steps * step, 10)
                trial[h2] = round(row[h2] + steps * step, 10)
                if trial[h] > 0:
                    out.append(trial)
    return out


def climb(
    cfg: BuyRiskConfig,
    k: int,
    mask: tuple[bool, ...],
    start: list[float],
    mx: float,
    cost: float,
    buy: str,
) -> list[float] | None:
    paying = [h for h, z in enumerate(mask) if not z]
    capped = payout_capped(cfg, mx * cost, cost)
    if cfg.fix_last_catch_on_climb and k >= 8 and not capped:
        body = paying[:-2]
    else:
        body = [h for h in paying if h != k]
    best = list(start)
    if not shape_ok(k, mask, best, mx):
        return None
    best_score = score(cfg, k, mask, best, mx, cost, buy)
    improved = True
    guards = 0
    while improved and guards < cfg.climb_guards:
        guards += 1
        improved = False
        for trial in neighbours(cfg, best, body, cost):
            trial[k] = mx
            if cfg.fix_last_catch_on_climb and k >= 8 and not capped:
                trial = fix_last_catch(k, mask, trial, mx, cost, capped=False)
            if not shape_ok(k, mask, trial, mx):
                continue
            sc = score(cfg, k, mask, trial, mx, cost, buy)
            if sc < best_score:
                best, best_score, improved = trial, sc, True
    return best if legal(cfg, k, mask, best, mx, cost, buy) else None


def retarget_buy_row(
    cfg: BuyRiskConfig, k: int, buy: str = "buy10"
) -> list[float]:
    """Cost-unit row for pick k on this chip under cfg."""
    ladder = (
        cfg.json_max_ladder_buy100
        if buy == "buy100" and cfg.json_max_ladder_buy100 is not None
        else cfg.json_max_ladder
    )
    if k not in ladder:
        raise KeyError(
            f"{cfg.risk}: pick_{k} has no json_max_ladder entry "
            "(medium/high stubs need designed tops before generate)"
        )
    cost = BUY_COSTS[buy]
    mask = zero_mask_for(cfg, k, buy)
    mx = floor_json_to_cost(json_max_for(cfg, k, cost), cost)
    seeds: list[list[float]] = []
    if cfg.use_geometric_seed:
        seeds.append(seed_geometric(cfg, k, mask, mx, cost, buy))
    seeds.append(seed_from_shares(cfg, k, mask, mx, cost, buy))
    adapted = adapt_baked_seed(cfg, k, mx, cost, buy)
    if adapted is not None:
        seeds.append(adapted)
    # Hit-or-miss Lumen: a lock-clean geometric already in the RTP window.
    # Hill-climb from a thin always-on-10× leftover seed never reaches it.
    paying_hits = [h for h, z in enumerate(mask) if not z]
    capped = payout_capped(cfg, mx * cost, cost)
    constructed = solve_row(
        coeff_for(cfg, k, mask, buy),
        k,
        paying_hits,
        mx,
        RTP_WINDOW,
        full_card=True,
        lock=lock_for(cost, pick=k, capped=capped),
    )
    if constructed is not None:
        if legal(cfg, k, mask, constructed, mx, cost, buy):
            return constructed
        seeds.insert(0, constructed)
    if cfg.prefer_exact_baked:
        chart = cfg.baked.get(buy) or cfg.baked.get("buy10")
        if chart is not None and k in chart:
            baked = [m / cost for m in chart[k]]
            if abs(baked[k] - mx) < 1e-12 and legal(cfg, k, mask, baked, mx, cost, buy):
                return baked
            if abs(baked[k] - mx) < 1e-12:
                seeds.insert(0, baked)
    best: list[float] | None = None
    best_score = None
    capped = payout_capped(cfg, mx * cost, cost)
    for seed in seeds:
        if cfg.fix_last_catch_on_climb and k >= 8 and not capped:
            seed = fix_last_catch(k, mask, seed, mx, cost, capped=False)
        climbed = climb(cfg, k, mask, seed, mx, cost, buy)
        if climbed is None:
            continue
        sc = score(cfg, k, mask, climbed, mx, cost, buy)
        if best_score is None or sc < best_score:
            best, best_score = climbed, sc
    if best is None:
        raise RuntimeError(
            f"{buy} {cfg.risk} pick_{k}: no legal 0.9650 buy row under JSON max "
            f"{json_max_for(cfg, k, cost)}"
        )
    return best


def generate_buy_chart(
    cfg: BuyRiskConfig, buy: str = "buy10"
) -> dict[int, list[float]]:
    """JSON-unit chart for every pick on this chip's max ladder."""
    cost = BUY_COSTS[buy]
    ladder = (
        cfg.json_max_ladder_buy100
        if buy == "buy100" and cfg.json_max_ladder_buy100 is not None
        else cfg.json_max_ladder
    )
    return {
        k: to_json_row(retarget_buy_row(cfg, k, buy), cost)
        for k in sorted(ladder)
    }


def cost_row_for_cfg(
    cfg: BuyRiskConfig, k: int, buy: str
) -> list[float]:
    """Designed baked row in cost units (solver pin)."""
    cost = BUY_COSTS[buy]
    chart = cfg.baked.get(buy) or cfg.baked.get("buy10")
    if chart is None or k not in chart:
        raise KeyError(f"{cfg.risk} {buy} pick_{k}: no baked chart")
    return [m / cost for m in chart[k]]


# ---------------------------------------------------------------------------
# Medium / high — designed BuyRiskConfig lives in easy_buy_medium / easy_buy_high.
# risk_stub lazy-imports so buy_bonus stays free of a circular import at load.
# ---------------------------------------------------------------------------


def risk_stub(risk: str) -> BuyRiskConfig:
    """Return the registered BuyRiskConfig for a risk name."""
    if risk == "medium":
        from easy_buy_medium import MEDIUM_BUY_CONFIG

        return MEDIUM_BUY_CONFIG
    if risk == "high":
        from easy_buy_high import HIGH_BUY_CONFIG

        return HIGH_BUY_CONFIG
    if risk == "low":
        from easy_buy_low import LOW_BUY_CONFIG

        return LOW_BUY_CONFIG
    if risk == "classic":
        from easy_buy_classic import CLASSIC_BUY_CONFIG

        return CLASSIC_BUY_CONFIG
    raise KeyError(f"buy_bonus.risk_stub({risk!r}): unknown risk")
