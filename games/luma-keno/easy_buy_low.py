"""Buy `low` (Easy analogue) — thin risk wrapper over `buy_bonus`.

Off `low` (`easy_off_low.py`) and Earn `low` (`easy_earn_low.py`) are Easy
leftover-share charts. Buy chips are the same risk family with a different
settlement contract (extras bought + placed Lumen + Pulse). Shared solver:
`buy_bonus.py`.

JSON tops are *not* pinned to Off Easy max. Picks 2–3 stay at 2.6; picks 4–5
use gradual tops (pick 4 below Off); picks 6–10 clear Off. Geometric seeding
keeps mid→top gradual (pick 4 → [0, 0.2, 0.6, 2.3, 8]).

Scope: **Buy low only.** Other risks plug in via their own `BuyRiskConfig`.
"""

from __future__ import annotations

from buy_bonus import (
    BUY_COSTS,
    RTP_WINDOW,
    BuyRiskConfig,
    cost_row_for_cfg,
    generate_buy_chart,
    json_max_for,
    legal,
    retarget_buy_row,
    to_json_row,
)
from easy_off_low import EASY_HUD, EASY_OFF_LOW
from keno_pick_one import lumen_placed_on_pick, settled_stats

# Re-export shared constants for solve_paytables / callers.
__all__ = [
    "BUY_COSTS",
    "EASY_BUY_LOW",
    "EASY_BUY_LOW_BUY100",
    "EASY_BUY_LOW_PICK1",
    "JSON_MAX_LADDER",
    "LOW_BUY_CONFIG",
    "RTP_WINDOW",
    "ZERO_MASK",
    "cost_row_for",
    "easy_buy_low_summary",
    "generate_easy_buy_low",
    "json_max_for_low",
    "retarget_easy_buy_row",
    "to_json_row",
]

#: JSON (base-bet) advertised max. NOT pinned to Off Easy max.
JSON_MAX_LADDER = {
    # Hit-or-miss Lumen (P=0.25): 2.6 cannot land 0.965 on the 0.1× lattice
    # under ratio_min 1.25. 4.8 / 2.6 is the unique pick-2 window point at 0.9650.
    2: 4.8,
    3: 5.4,
    # Picks 4–5: tops lowered so mid→top is gradual. Placed-Lumen coeffs on
    # early hits are huge, so a high JSON top eats RTP and forces tiny body
    # cells — the 0.7→30 cliff on pick 4. Prefer gradual feel over clearing
    # Off Easy max (pick 4 Off=22.5; pick 5 still clears Off 36 at 40).
    4: 8.0,
    5: 40.0,
    6: 60.0,  # lowered from 100 for gradual mid→top
    7: 120.0,
    8: 160.0,
    9: 180.0,
    10: 200.0,
}

#: Zero mask per pick (True = advertised 0). Easy HUD for 2–4 / 6 / 8; deeper
#: zeros on 5 / 7 / 9–10 so shape_lock last-catch (≥8×) can clear under the
#: raised buy tops.
ZERO_MASK = {
    2: (True, False, False),
    3: (True, False, False, False),
    4: (True, False, False, False, False),
    5: (True, True, False, False, False, False),
    6: (True, True, False, False, False, False, False),
    7: (True, True, True, False, False, False, False, False),
    8: (True, True, True, False, False, False, False, False, False),
    9: (True, True, True, False, False, False, False, False, False, False),
    10: (True, True, True, False, False, False, False, False, False, False, False),
}

#: Shipped Buy `low` chart for buy10 (picks 2–10). buy100 has a separate
#: ladder (EASY_BUY_LOW_BUY100) so the upsell strip is not dominated.
EASY_BUY_LOW: dict[int, list[float]] = {
    2: [0.0, 2.6, 4.8],
    3: [0.0, 2.1, 3.9, 5.4],
    4: [0.0, 0.5, 3.8, 6.4, 8.0],
    5: [0.0, 0.0, 0.7, 5.3, 25.5, 40.0],
    6: [0.0, 0.0, 1.0, 3.1, 9.0, 48.0, 60.0],
    7: [0.0, 0.0, 0.0, 1.9, 6.4, 28.0, 95.9, 120.0],
    8: [0.0, 0.0, 0.0, 2.5, 6.5, 8.4, 10.6, 32.0, 160.0],
    9: [0.0, 0.0, 0.0, 2.3, 4.3, 7.4, 9.5, 12.0, 36.0, 180.0],
    10: [0.0, 0.0, 0.0, 1.8, 3.4, 6.4, 8.0, 10.0, 12.5, 40.0, 200.0],
}

#: buy100 chart — diverged tops/bodies so buy100 is not the same strip
#: as buy10 (picks 2–10). Pick 1 remains chip-specific below.
EASY_BUY_LOW_BUY100: dict[int, list[float]] = {
    2: [0.0, 2.8, 5.2],
    3: [0.0, 2.8, 3.9, 5.5],
    4: [0.0, 1.2, 3.7, 7.0, 9.0],
    5: [0.0, 0.0, 0.8, 6.2, 24.3, 48.0],
    6: [0.0, 0.0, 1.2, 2.3, 11.0, 64.0, 80.0],
    7: [0.0, 0.0, 0.0, 1.9, 9.8, 18.5, 116.0, 145.0],
    8: [0.0, 0.0, 0.0, 1.2, 5.6, 20.1, 32.0, 40.0, 200.0],
    9: [0.0, 0.0, 0.0, 1.7, 5.0, 7.6, 25.6, 32.0, 40.0, 200.0],
    10: [0.0, 0.0, 0.0, 1.3, 2.7, 7.5, 20.4, 25.6, 32.0, 40.0, 200.0],
}


#: pick_1 is chip-specific (not placed; lattice search in solve_paytables).
EASY_BUY_LOW_PICK1: dict[str, list[float]] = {
    "buy10": [1.6, 3.0],
    "buy100": [0.1, 3.5],
}

LOW_BUY_CONFIG = BuyRiskConfig(
    risk="low",
    json_max_ladder=JSON_MAX_LADDER,
    zero_mask=ZERO_MASK,
    hud=EASY_HUD,
    baked={"buy10": EASY_BUY_LOW, "buy100": EASY_BUY_LOW_BUY100},
    json_max_ladder_buy100={
        2: 5.2,  # 100× hit-or-miss lattice; 4.8 is buy10-only
        3: 5.5,
        **{
            k: max(JSON_MAX_LADDER[k], EASY_BUY_LOW_BUY100[k][-1])
            for k in EASY_BUY_LOW_BUY100
            if k not in (2, 3)
        },
    },
    pick1=EASY_BUY_LOW_PICK1,
    off_chart=EASY_OFF_LOW,
    apply_payout_cap=False,
    use_geometric_seed=True,
    fix_last_catch_on_climb=False,
    neighbour_deltas=(-8, -5, -3, -2, -1, 1, 2, 3, 5, 8),
    transfer_steps=(1, 2, 3, 5, 8, 12),
    climb_guards=100,
    prefer_exact_baked=True,  # ship soft pick10 last-catch as designed
    buy_bonus_min_pick=4,
    earn_how_to_cap={8: 400.0, 9: 400.0, 10: 400.0},
)


def json_max_for_low(k: int, cost: float) -> float:
    return json_max_for(LOW_BUY_CONFIG, k, cost)


def retarget_easy_buy_row(k: int, buy: str = "buy10") -> list[float]:
    """Cost-unit row for pick k on this chip."""
    return retarget_buy_row(LOW_BUY_CONFIG, k, buy)


def generate_easy_buy_low(buy: str = "buy10") -> dict[int, list[float]]:
    """JSON-unit chart for picks 2–10."""
    return generate_buy_chart(LOW_BUY_CONFIG, buy)


def cost_row_for(k: int, buy: str) -> list[float]:
    """Designed row in cost units for the solver."""
    return cost_row_for_cfg(LOW_BUY_CONFIG, k, buy)


def _validate() -> None:
    from buy_bonus import zero_mask_for as _zmf

    for buy, chart in (("buy10", EASY_BUY_LOW), ("buy100", EASY_BUY_LOW_BUY100)):
        cost = BUY_COSTS[buy]
        generated = generate_easy_buy_low(buy)
        prev_max = None
        for k, row in sorted(chart.items()):
            assert row == generated[k], (
                f"{buy} pick_{k}: baked {row} != generator {generated[k]}"
            )
            assert len(row) == k + 1
            mask = _zmf(LOW_BUY_CONFIG, k, buy)
            assert [m == 0 for m in row] == list(mask), (
                f"{buy} pick_{k}: zero mask diverges from designed mask"
            )
            expected_top = json_max_for_low(k, cost)
            assert abs(max(row) - expected_top) < 1e-9, (
                f"{buy} pick_{k}: JSON top {max(row)} != designed {expected_top}"
            )
            if prev_max is not None:
                assert max(row) + 1e-9 >= prev_max, (
                    f"{buy} pick_{k}: JSON top {max(row)} < pick_{k-1} {prev_max}"
                )
            prev_max = max(row)
            paying = [m for m in row if m > 0]
            assert all(b > a for a, b in zip(paying, paying[1:]))
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            assert legal(LOW_BUY_CONFIG, k, mask, crow, crow[k], cost, buy), (
                f"{buy} pick_{k}: not legal under buy settlement"
            )
            stats = settled_stats(
                "low", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            if k >= 8:
                earn_how = 100.0 * 4.0
                assert stats["max_m"] <= earn_how + 1e-9, (
                    f"{buy} pick_{k}: vs-debit {stats['max_m']} > Earn How-to {earn_how}"
                )


_validate()


def easy_buy_low_summary() -> str:
    lines = []
    for buy, cost in BUY_COSTS.items():
        j1 = EASY_BUY_LOW_PICK1[buy]
        crow1 = [m / cost for m in j1]
        s1 = settled_stats(
            "low", 1, crow1, bought=True, placed=False, cost=cost, buy=buy
        )
        lines.append(
            f"low_pick_1_{buy} {j1} rtp={s1['rtp']:.6f} "
            f"edge={1 - s1['rtp']:.4%} (lumen hit/miss modeled)"
        )
        for k, row in sorted(EASY_BUY_LOW.items()):
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            stats = settled_stats(
                "low", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            cells = " / ".join(f"{m:g}" for m in row if m > 0)
            lines.append(
                f"low_pick_{k:<2d}_{buy} [{cells}] "
                f"rtp={stats['rtp']:.6f} edge={1 - stats['rtp']:.4%} "
                f"hr={stats['hit_rate']:.4f} how={stats['max_m']:.0f} "
                f"placed={int(placed)}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_buy_low_summary())
