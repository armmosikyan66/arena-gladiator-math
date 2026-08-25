#!/usr/bin/env python3
"""Solve luma-keno paytables: pool 40, drawn 10, picks 1-10, 4 risk modes.

Publish gates (Stake Engine dashboard — binding, stricter than the local
rgs_verification warnings):
  - every mode must award a non-zero win at least 1 in 50 (hit rate >= 2%);
  - per-mode RTP <= 0.967 (3-star volatility limit);
  - Cross-Mode RTP Consistency: max-min RTP <= 0.50pp.

pick_1 is one multiplier per hit on the 0.950 lattice (the only legal
two-outcome 0.1x pair under the 0.967 cap). Picks 2-10 share RTP ~0.9660.
A miss/hit remainder split is not used: each hit count has one payout.

Structure per (risk, k):
  - consolation tier at the first paying hit: sub-40x, fixed RTP share
    (keeps ETL40 under the 0.9 gate) and lifts the hit rate above the
    1-in-50 floor,
  - classic/low only: a fixed 0.5x refund one hit below pay start when
    P(h) <= 0.35 (Stake Originals Low-style "gentle bleed"; 0.5x = 50 LUT
    units, legal on the 0.1x grid). medium/high stay jackpot-shaped,
  - remaining budget water-filled over rarer hits, m_h = c * P(h)^-beta,
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

from keno_pick_one import pick_one_row

POOL = 40
DRAWN = 10
PICKS = range(1, 11)

RTP_TARGET = 0.9660
RTP_TOL = 0.0005  # grid-search convergence tolerance
MODE_RTP_BAND = (0.9645, 0.9665)
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
PAY_START = {
    "classic": {2: 1, 3: 1, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 4},
    "low": {2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4},
    "medium": {2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 5},
    "high": {2: 1, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 4, 9: 5, 10: 5},
}

# Refund tier: classic/low only. One hit below the pay start pays a fixed
# REFUND_X (0.5x = 50 LUT units — legal: multiple of 10). This mirrors Stake
# Originals Low risk (pays small amounts on low hits: "a gentle bleed");
# medium/high stay jackpot-shaped (Stake High pays nothing until 3-4 hits).
# Guard: only where P(h) <= REFUND_P_MAX — a refund on a likely outcome
# (e.g. classic pick_4 h=1, P=0.44) burns over a fifth of the RTP budget.
# pick_2/pick_3 have no tier below start (h would be 0), so no refund there.
REFUND_RISKS = ("classic", "low")
REFUND_X = 0.5
REFUND_P_MAX = 0.35

# Cap ladder by distance below the top hit: fraction of risk top, and an
# absolute ceiling so big headline prizes cannot drag mid tiers up.
CAP_FRACTION = [1.0, 0.6, 0.4, 0.3, 0.2]
CAP_ABSOLUTE = [float("inf"), 2500.0, 1500.0, 1000.0, 1000.0]

# Local verifier limits (rgs_verification.py) minus margin.
GATES = {
    "p5k": 0.009,
    "p10k": 0.0045,
    "etl40": 0.88,
    "etl10k": 0.70,
    "cvar": 700.0,
    "std": 55.0,
    "max_m": 10000.0,
}


def hit_weight(k: int, h: int) -> int:
    rest = POOL - DRAWN
    if h < 0 or h > k or (k - h) > rest or h > DRAWN:
        return 0
    return math.comb(DRAWN, h) * math.comb(rest, k - h)


def probabilities(k: int) -> list[float]:
    total = math.comb(POOL, k)
    return [hit_weight(k, h) / total for h in range(k + 1)]


def cap_for(risk: str, k: int, h: int) -> float:
    dist = min(k - h, len(CAP_FRACTION) - 1)
    return min(RISK_SHAPES[risk]["top"] * CAP_FRACTION[dist], CAP_ABSOLUTE[dist])


def tail_capacity_of(p: list[float], tail: list[int], caps: dict) -> float:
    return sum(p[h] * caps[h] for h in tail)


def _table_valid(m: list[float], start: int, k: int, caps: dict) -> bool:
    if any(m[h] < 0.1 - 1e-9 for h in range(start, k + 1)):
        return False
    if any(m[h] > caps[h] + 1e-9 for h in range(start, k + 1)):
        return False
    # m[start - 1] is the fixed refund tier (if any); it must not exceed start.
    if start >= 1 and m[start - 1] > 0 and m[start] < m[start - 1] - 1e-9:
        return False
    return all(m[h + 1] >= m[h] - 1e-9 for h in range(start, k))


def _grid_moves(m: list[float], start: int, k: int, caps: dict):
    """Single +/-0.1 moves that keep floors, caps and monotonicity."""
    for h in range(start, k + 1):
        floor = m[start - 1] + 0.1 if h == start and start >= 1 and m[start - 1] > 0 else (0.1 if h == start else m[h - 1] + 0.1)
        ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - 0.1)
        for d in (0.1, -0.1):
            if floor - 1e-9 <= m[h] + d <= ceiling + 1e-9:
                yield h, d


def _refine(m: list[float], p: list[float], start: int, k: int, caps: dict) -> float:
    """Hill-climb |RTP - target| over single and paired 0.1x moves."""

    def err_of(table: list[float]) -> float:
        return sum(pi * mi for pi, mi in zip(p, table)) - RTP_TARGET

    best_err = err_of(m)
    for _ in range(5000):
        if abs(best_err) <= RTP_TOL:
            break
        improved = False
        for h, d in _grid_moves(m, start, k, caps):
            new_err = best_err + d * p[h]
            if abs(new_err) < abs(best_err) - 1e-12:
                m[h] = round(m[h] + d, 10)
                best_err = new_err
                improved = True
        if improved:
            continue
        # No single move helps: try pairs (+0.1 on one tier, -0.1 on another).
        pair = None
        for h1, d1 in _grid_moves(m, start, k, caps):
            if d1 != 0.1:
                continue
            for h2, d2 in _grid_moves(m, start, k, caps):
                if d2 != -0.1 or h2 == h1:
                    continue
                cand = list(m)
                cand[h1] = round(cand[h1] + 0.1, 10)
                cand[h2] = round(cand[h2] - 0.1, 10)
                if not _table_valid(cand, start, k, caps):
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


def refund_hit(risk: str, k: int) -> int | None:
    """Hit count that pays the fixed REFUND_X, or None when not applicable.

    One below the pay start, classic/low only, and only where the refund is
    affordable (P(h) <= REFUND_P_MAX). pick_2/pick_3 pay from 1 hit, so
    there is no tier below start to refund.
    """
    if risk not in REFUND_RISKS:
        return None
    h = PAY_START[risk][k] - 1
    if h < 1:
        return None
    if probabilities(k)[h] > REFUND_P_MAX:
        return None
    return h


def _fill_from(risk: str, k: int, start_pay: float | None) -> list[float]:
    """Water-fill + grid-converge with a fixed (or designed) consolation pay."""
    p = probabilities(k)
    beta = RISK_SHAPES[risk]["beta"]
    start = PAY_START[risk][k]
    caps = {h: cap_for(risk, k, h) for h in range(start, k + 1)}
    tail = [h for h in range(start + 1, k + 1)]
    rh = refund_hit(risk, k)
    refund_cost = p[rh] * REFUND_X if rh is not None else 0.0
    # With a refund tier below start, keep monotonicity: start >= refund + 0.1.
    min_start = REFUND_X + 0.1 if rh is not None else 0.1
    caps = {h: max(v, min_start) if h == start else v for h, v in caps.items()}

    sub40_budget = min(RISK_SHAPES[risk]["sub40"] * RTP_TARGET, p[start] * min(39.9, caps[start]))
    if start_pay is None:
        m_start = max(min_start, round(sub40_budget / p[start] * 10) / 10)
        m_start = min(m_start, 39.9, caps[start])
    else:
        m_start = min(max(min_start, round(start_pay * 10) / 10), 39.9, caps[start])
    # Never let the consolation alone overshoot the target: remaining budget
    # must stay >= 0 so the tail fill is well-defined. The refund tier below
    # start is fixed and spends its budget first.
    m_start = min(m_start, math.floor((RTP_TARGET - refund_cost) / p[start] * 10 - 1e-9) / 10)

    m = [0.0] * (k + 1)
    if rh is not None:
        m[rh] = REFUND_X
    m[start] = m_start
    remaining = RTP_TARGET - p[start] * m[start] - refund_cost

    if tail:
        def total_for(c: float) -> float:
            return sum(p[h] * min(c * p[h] ** -beta, caps[h]) for h in tail)

        lo, hi = 0.0, 1.0
        while total_for(hi) < remaining:
            hi *= 2.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if total_for(mid) < remaining:
                lo = mid
            else:
                hi = mid
        c = (lo + hi) / 2
        for h in tail:
            m[h] = round(min(c * p[h] ** -beta, caps[h]) * 10) / 10
            # Keep payouts non-decreasing across hits even when the shape
            # wants a dip right above the consolation tier.
            m[h] = max(m[h], round(m[h - 1] * 10 + 1) / 10)

    # Grid rounding: floor every tier to 0.1x, then buy the leftover back
    # with 0.1x steps (largest coin that fits, smallest overshoot otherwise).
    def rtp() -> float:
        return sum(pi * mi for pi, mi in zip(p, m))

    for h in range(start, k + 1):
        if m[h] > 0:
            m[h] = math.floor(m[h] * 10 + 1e-9) / 10
            m[h] = max(min_start if h == start else 0.1, m[h])

    for _ in range(2000):
        leftover = RTP_TARGET - rtp()
        if abs(leftover) <= RTP_TOL:
            break
        if leftover < 0:
            best = None
            for h in range(start, k + 1):
                floor_h = min_start if h == start else m[h - 1] + 0.1
                if m[h] - 0.1 < floor_h - 1e-9:
                    continue
                coin = p[h] * 0.1
                if best is None or coin < best[0]:
                    best = (coin, h)
            if best is None:
                break
            m[best[1]] = round(m[best[1]] - 0.1, 10)
            continue
        best = None  # (coin, h)
        for h in range(start, k + 1):
            coin = p[h] * 0.1
            ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - 0.1)
            if m[h] + 0.1 > ceiling + 1e-9:
                continue
            if coin <= leftover + 1e-12 and (best is None or coin > best[0]):
                best = (coin, h)
        if best is None:
            for h in range(start, k + 1):
                coin = p[h] * 0.1
                ceiling = caps[h] if h == k else min(caps[h], m[h + 1] - 0.1)
                if m[h] + 0.1 > ceiling + 1e-9:
                    continue
                if best is None or coin < best[0]:
                    best = (coin, h)
        if best is None:
            break
        m[best[1]] = round(m[best[1]] + 0.1, 10)

    _refine(m, p, start, k, caps)
    return m


def solve_table(risk: str, k: int) -> tuple[list[float], list[str]]:
    errors: list[str] = []
    p = probabilities(k)
    start = PAY_START[risk][k]
    caps = {h: cap_for(risk, k, h) for h in range(start, k + 1)}
    tail = [h for h in range(start + 1, k + 1)]
    rh = refund_hit(risk, k)
    refund_cost = p[rh] * REFUND_X if rh is not None else 0.0
    min_start = REFUND_X + 0.1 if rh is not None else 0.1

    # Consolation tier: sub-40x, fixed RTP share. The cap ladder and the
    # water-fill shape already leave the tail below target on its own, so the
    # consolation share is used as-is unless caps make it impossible.
    sub40_budget = RISK_SHAPES[risk]["sub40"] * RTP_TARGET
    max_consolation = p[start] * min(39.9, caps[start])
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

    # The designed fill can strand the RTP on the wrong side of a lattice
    # gap (e.g. pick_2: [0, 0.5, 13.1] = 0.9481 while [0, 0.1, 15.8] is
    # exactly 0.95). When it misses tolerance, scan the consolation pay
    # over the 0.1x grid and keep the variant landing closest to target;
    # ties prefer the larger consolation (better hit-rate feel).
    designed = _fill_from(risk, k, None)
    best = (abs(err_of(designed)), designed)
    if best[0] > RTP_TOL * 2:
        lo_pay = min_start
        hi_pay = min(39.9, caps[start], max(2.0, round(sub40_budget / p[start] * 2 * 10) / 10))
        steps = int(round((hi_pay - lo_pay) / 0.1)) + 1
        for i in range(steps):
            cand_pay = round(lo_pay + 0.1 * i, 10)
            cand = _fill_from(risk, k, cand_pay)
            if not _table_valid(cand, start, k, caps):
                continue
            cand_err = abs(err_of(cand))
            if cand_err < best[0] - 1e-9 or (
                abs(cand_err - best[0]) <= 1e-9 and cand[start] > best[1][start]
            ):
                best = (cand_err, cand)

    m = best[1]
    residual = best[0]
    if residual > RTP_TOL * 4:
        errors.append(f"grid convergence residual {residual:.5f}")

    if not _table_valid(m, start, k, caps):
        errors.append("cap or monotonicity violated after grid search")
    return m, errors


def mode_stats(k: int, table: list[float]) -> dict:
    pays = table
    p = probabilities(k)
    rtp = sum(pi * mi for pi, mi in zip(p, pays))
    var = sum(pi * (mi - rtp) ** 2 for pi, mi in zip(p, pays))

    ranked = sorted(zip(pays, p))
    p5k = sum(pi for mi, pi in ranked if mi >= 5000)
    p10k = sum(pi for mi, pi in ranked if mi >= 10000)
    etl40 = sum(pi * mi for mi, pi in ranked if mi >= 40)
    etl10k = sum(pi * mi for mi, pi in ranked if mi >= 10000)

    cum = 0.0
    tail_start = ranked[0][0]
    for mi, pi in ranked:
        cum += pi
        if cum >= 0.999:
            tail_start = mi
            break
    tail_p = sum(pi for mi, pi in ranked if mi >= tail_start)
    cvar = (sum(pi * mi for mi, pi in ranked if mi >= tail_start) / tail_p) if tail_p else 0.0

    return {
        "rtp": rtp,
        "std": math.sqrt(var),
        "p5k": p5k,
        "p10k": p10k,
        "etl40": etl40,
        "etl10k": etl10k,
        "cvar": cvar,
        "max_m": max(pays),
        "hit_rate": sum(pi for mi, pi in ranked if mi > 0),
        "nonzero_payouts": sorted({mi for mi in pays if mi > 0}),
    }


def check_gates(k: int, stats: dict) -> list[str]:
    f: list[str] = []
    lo, hi = MODE_RTP_BAND
    # pick_1 is lattice-locked at 0.950; the 0.966 band applies to k >= 2.
    if k != 1 and not (lo <= stats["rtp"] <= hi):
        f.append(f"rtp={stats['rtp']:.4f} outside {lo:.4f}-{hi:.4f}")
    if k == 1 and abs(stats["rtp"] - 0.95) > 1e-9:
        f.append(f"rtp={stats['rtp']:.4f} != 0.950 lattice")
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
    if stats["cvar"] > GATES["cvar"]:
        f.append(f"cvar={stats['cvar']:.0f}")
    if stats["std"] > GATES["std"]:
        f.append(f"std={stats['std']:.1f}")
    if stats["max_m"] > GATES["max_m"]:
        f.append(f"max_m={stats['max_m']:.0f}")
    # k >= 2 needs at least two paying tiers.
    if len(stats["nonzero_payouts"]) < 2:
        f.append("fewer than 2 nonzero payouts")
    return f


def solve_all() -> dict:
    risks: dict[str, dict[str, list[float]]] = {}
    band_rtps: list[float] = []
    all_rtps: list[float] = []
    failures: dict[str, list[str]] = {}
    for risk in ("classic", "low", "medium", "high"):
        tables: dict[str, list[float]] = {}
        for k in PICKS:
            name = f"{risk}_pick_{k}"
            if k == 1:
                table, errors = pick_one_row(risk), []
            else:
                table, errors = solve_table(risk, k)
            stats = mode_stats(k, table)
            fails = errors + check_gates(k, stats)
            if fails:
                failures[name] = fails
            tables[str(k)] = table
            all_rtps.append(stats["rtp"])
            if k >= 2:
                band_rtps.append(stats["rtp"])
            print(
                f"{name:16s} rtp={stats['rtp']:.4f} std={stats['std']:6.2f} "
                f"max={stats['max_m']:8.1f} hr={stats['hit_rate']:.4f} "
                f"etl40={stats['etl40']:.3f} cvar={stats['cvar']:6.1f} "
                f"p5k={stats['p5k']:.1e} p10k={stats['p10k']:.1e} "
                f"{'FAIL ' + '; '.join(fails) if fails else 'ok'}"
            )
            print(f"{'':16s} {table}")
        risks[risk] = tables
    spread = max(all_rtps) - min(all_rtps)
    band_spread = max(band_rtps) - min(band_rtps)
    print(f"\nmode RTP spread={spread:.4f} (incl. pick_1 0.95 lattice)")
    print(f"picks 2-10 spread={band_spread:.4f} (dashboard limit {SPREAD_MAX})")
    print(f"min hit rate={min(mode_stats(k, risks[r][str(k)])['hit_rate'] for r in risks for k in PICKS):.4f}")
    if band_spread > SPREAD_MAX:
        failures["spread"] = [f"{band_spread:.4f} > {SPREAD_MAX}"]
    if failures:
        raise SystemExit(f"gate failures: {failures}")
    return risks


def write_outputs(risks: dict) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    payload = {
        "pool": POOL,
        "drawn": DRAWN,
        "rtp_target": RTP_TARGET,
        "picks": {"min": 1, "max": 10},
        "risks": risks,
    }
    game_path = os.path.join(here, "paytables.json")
    with open(game_path, "w", encoding="UTF-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"wrote {game_path}")

    web_dir = os.path.abspath(os.path.join(here, "..", "..", "..", "web", "src", "data"))
    os.makedirs(web_dir, exist_ok=True)
    web_payload = dict(payload)
    web_payload["wallet"] = {
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
    web_path = os.path.join(web_dir, "keno-paytables.json")
    with open(web_path, "w", encoding="UTF-8") as handle:
        json.dump(web_payload, handle, indent=2)
    print(f"wrote {web_path}")


if __name__ == "__main__":
    write_outputs(solve_all())
