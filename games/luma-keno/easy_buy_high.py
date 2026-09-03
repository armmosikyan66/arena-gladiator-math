"""Buy `high` — thin risk wrapper over `buy_bonus`.

Off `high` (`easy_off_high.py`) is a max-anchored geometric HUD. Buy chips
use the shared buy-bonus leftover/lock path (`buy_bonus.py`) with high-
specific tops and deeper zero masks. Placed Lumen + Pulse force JSON tops
well under Off high — prefer gradual hit-to-hit steps over Off/cap cliffs
(old buy10 pick 6 was 0.9→996).

How-to vs debit = 2 × JSON. Deep picks stay ≤ Earn high How-to and the
dashboard Max Payout pin (buy10 JSON ≤ 2250; buy100 deep tops sit under
the 450 pin on a separate ladder).

Scope: **Buy high only.** buy100 uses a separate JSON_MAX ladder + baked
bodies — 100× Lumen cannot fund buy10 deep tops without cliffs / illegal RTP.
"""

from __future__ import annotations

from buy_bonus import (
    BUY_COSTS,
    RTP_WINDOW,
    BuyRiskConfig,
    cost_row_for_cfg,
    generate_buy_chart,
    json_max_for as shared_json_max_for,
    legal,
    retarget_buy_row,
    to_json_row,
)
from easy_off_high import HIGH_OFF
from keno_pick_one import lumen_placed_on_pick, settled_stats

__all__ = [
    "BUY_COSTS",
    "EASY_BUY_HIGH",
    "EASY_BUY_HIGH_BUY100",
    "EASY_BUY_HIGH_PICK1",
    "HIGH_BUY_CONFIG",
    "JSON_MAX_LADDER",
    "JSON_MAX_LADDER_BUY100",
    "RTP_WINDOW",
    "ZERO_MASK",
    "ZERO_MASK_BUY100",
    "cost_row_for",
    "easy_buy_high_summary",
    "generate_easy_buy_high",
    "json_max_for",
    "retarget_easy_buy_row",
    "to_json_row",
]

#: JSON (base-bet) advertised max for buy10. NOT pinned to Off high max.
JSON_MAX_LADDER = {
    2: 4.8,  # hit-or-miss Lumen: 4.8/2.6 is the 0.9650 lattice point
    3: 5.4,
    4: 22.0,  # top-heavy vs classic 18 / medium 12
    5: 80.0,  # deeper zeros than medium; Off 900 was unreachable without cliffs
    6: 250.0,
    7: 600.0,
    8: 1200.0,
    9: 1800.0,
    10: 2250.0,  # Max Payout pin for buy10
}

ZERO_MASK = {
    2: (True, False, False),
    3: (True, False, False, False),
    4: (True, True, False, False, False),
    5: (True, True, True, False, False, False),  # hit-3 open to hold etl40
    6: (True, True, True, True, False, False, False),
    7: (True, True, True, False, False, False, False, False),
    8: (True, True, True, True, False, False, False, False, False),
    9: (True, True, True, False, False, False, False, False, False, False),
    10: (True, True, True, False, False, False, False, False, False, False, False),
}

EASY_BUY_HIGH: dict[int, list[float]] = {
    2: [0.0, 2.6, 4.8],
    3: [0.0, 2.1, 3.9, 5.4],
    4: [0.0, 0.0, 1.3, 13.6, 22.0],
    5: [0.0, 0.0, 0.0, 4.5, 32.7, 80.0],
    6: [0.0, 0.0, 0.0, 0.0, 18.9, 65.1, 250.0],
    7: [0.0, 0.0, 0.0, 0.9, 5.3, 39.0, 117.4, 600.0],
    8: [0.0, 0.0, 0.0, 0.0, 6.2, 9.8, 80.0, 240.0, 1200.0],
    9: [0.0, 0.0, 0.0, 1.1, 3.8, 9.9, 16.7, 57.7, 200.0, 1800.0],
    10: [0.0, 0.0, 0.0, 0.8, 2.8, 6.5, 12.7, 43.8, 152.3, 529.4, 2250.0],
}

#: buy100 JSON tops — climbing, under Max Payout 450, well below buy10 deep
#: tops so the advertised chart is not the same strip at 100× Lumen.
JSON_MAX_LADDER_BUY100 = {
    2: 5.2,
    3: 5.5,
    4: 25.0,
    5: 70.0,  # diverge vs buy10 80
    6: 415.0,
    7: 420.0,
    8: 420.0,
    9: 420.0,
    10: 450.0,
}

ZERO_MASK_BUY100 = {
    4: (True, True, False, False, False),
    5: (True, True, True, False, False, False),
    6: (True, True, True, True, False, False, False),
    7: (True, True, True, True, False, False, False, False),
    8: (True, True, True, True, False, False, False, False, False),
    9: (True, True, True, True, False, False, False, False, False, False),
    10: (True, True, True, True, True, False, False, False, False, False, False),
}

EASY_BUY_HIGH_BUY100: dict[int, list[float]] = {
    2: [0.0, 2.8, 5.2],
    3: [0.0, 2.8, 3.9, 5.5],
    4: [0.0, 0.0, 1.7, 13.4, 25.0],
    5: [0.0, 0.0, 0.0, 4.6, 36.3, 70.0],
    6: [0.0, 0.0, 0.0, 0.0, 23.1, 40.3, 415.0],
    7: [0.0, 0.0, 0.0, 0.0, 6.6, 52.6, 79.5, 420.0],
    8: [0.0, 0.0, 0.0, 0.0, 3.8, 29.8, 40.8, 84.0, 420.0],
    9: [0.0, 0.0, 0.0, 0.0, 3.2, 10.0, 53.7, 67.2, 84.0, 420.0],
    10: [0.0, 0.0, 0.0, 0.0, 0.0, 8.9, 33.9, 73.6, 100.0, 360.0, 450.0],
}

EASY_BUY_HIGH_PICK1: dict[str, list[float]] = {
    "buy10": [1.7, 3.1],
    "buy100": [1.2, 3.6],
}

_HIGH_BUY_HUD = {
    k: [0.0 if ZERO_MASK[k][h] else 1.0 for h in range(k + 1)]
    for k in ZERO_MASK
}

HIGH_BUY_CONFIG = BuyRiskConfig(
    risk="high",
    json_max_ladder=JSON_MAX_LADDER,
    zero_mask=ZERO_MASK,
    hud=_HIGH_BUY_HUD,
    baked={"buy10": EASY_BUY_HIGH, "buy100": EASY_BUY_HIGH_BUY100},
    pick1=EASY_BUY_HIGH_PICK1,
    off_chart=HIGH_OFF,
    json_max_ladder_buy100=JSON_MAX_LADDER_BUY100,
    zero_mask_buy100=ZERO_MASK_BUY100,
    apply_payout_cap=True,
    use_geometric_seed=True,
    fix_last_catch_on_climb=True,
    neighbour_deltas=(-12, -8, -5, -3, -2, -1, 1, 2, 3, 5, 8, 12),
    transfer_steps=(1, 2, 3, 5, 8, 12, 20),
    climb_guards=200,
    prefer_exact_baked=True,
    buy_bonus_min_pick=None,
    earn_how_to_cap={8: 24400.0, 9: 50000.0, 10: 100000.0},
)


def json_max_for(k: int, cost: float) -> float:
    return shared_json_max_for(HIGH_BUY_CONFIG, k, cost)


def retarget_easy_buy_row(k: int, buy: str = "buy10") -> list[float]:
    return retarget_buy_row(HIGH_BUY_CONFIG, k, buy)


def generate_easy_buy_high(buy: str = "buy10") -> dict[int, list[float]]:
    return generate_buy_chart(HIGH_BUY_CONFIG, buy)


def cost_row_for(k: int, buy: str) -> list[float]:
    return cost_row_for_cfg(HIGH_BUY_CONFIG, k, buy)


def _validate() -> None:
    from buy_bonus import zero_mask_for

    for buy, chart in (("buy10", EASY_BUY_HIGH), ("buy100", EASY_BUY_HIGH_BUY100)):
        cost = BUY_COSTS[buy]
        generated = generate_easy_buy_high(buy)
        prev_max = None
        for k, row in sorted(chart.items()):
            assert row == generated[k], (
                f"{buy} pick_{k}: baked {row} != generator {generated[k]}"
            )
            assert len(row) == k + 1
            mask = zero_mask_for(HIGH_BUY_CONFIG, k, buy)
            assert [m == 0 for m in row] == list(mask), (
                f"{buy} pick_{k}: zero mask diverges from designed mask"
            )
            expected_top = json_max_for(k, cost)
            assert abs(max(row) - expected_top) < 1e-9, (
                f"{buy} pick_{k}: JSON top {max(row)} != designed {expected_top}"
            )
            if prev_max is not None:
                assert max(row) + 1e-9 >= prev_max
            prev_max = max(row)
            paying = [m for m in row if m > 0]
            assert all(b > a for a, b in zip(paying, paying[1:]))
            crow = [m / cost for m in row]
            assert legal(HIGH_BUY_CONFIG, k, mask, crow, crow[k], cost, buy), (
                f"{buy} pick_{k}: not legal under buy settlement"
            )
            stats = settled_stats(
                "high", k, crow, bought=True, placed=True, cost=cost, buy=buy
            )
            if k >= 8:
                earn_how = HIGH_BUY_CONFIG.earn_how_to_cap[k]
                assert stats["max_m"] <= earn_how + 1e-9


_validate()


def easy_buy_high_summary() -> str:
    lines = []
    for buy, cost in BUY_COSTS.items():
        j1 = EASY_BUY_HIGH_PICK1[buy]
        crow1 = [m / cost for m in j1]
        s1 = settled_stats(
            "high", 1, crow1, bought=True, placed=False, cost=cost, buy=buy
        )
        lines.append(
            f"high_pick_1_{buy} {j1} rtp={s1['rtp']:.6f} "
            f"edge={1 - s1['rtp']:.4%} (lumen hit/miss modeled)"
        )
        chart = EASY_BUY_HIGH if buy == "buy10" else EASY_BUY_HIGH_BUY100
        for k, row in sorted(chart.items()):
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            stats = settled_stats(
                "high", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            cells = " / ".join(f"{m:g}" for m in row if m > 0)
            lines.append(
                f"high_pick_{k:<2d}_{buy} [{cells}] "
                f"rtp={stats['rtp']:.6f} edge={1 - stats['rtp']:.4%} "
                f"hr={stats['hit_rate']:.4f} how={stats['max_m']:.0f} "
                f"placed={int(placed)}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_buy_high_summary())
