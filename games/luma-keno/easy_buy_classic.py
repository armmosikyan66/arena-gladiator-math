"""Buy `classic` — thin risk wrapper over `buy_bonus`.

Off `classic` (`easy_off_classic.py`) is a max-anchored geometric HUD. Buy
chips use the shared buy-bonus leftover/lock path (`buy_bonus.py`) with
classic-specific tops, zero masks, and Max Payout flooring on buy100.

Unlike the old Off-max pin, JSON tops come from JSON_MAX_LADDER — raised
above Off classic where placed-Lumen + Pulse still fit MODE_RTP_BAND.
Max Payout decision: keep MAX_PAYOUT_ABS[100]=90_000 (3-Star 100k − margin).
JSON ≤ 450 / How-to vs debit ≤ 900. Do not raise the abs cap — 100k only
buys JSON 500 and still cannot match buy10 vs-debit; absolute jackpot is
already higher (90k vs buy10 45k). Climb deep tops to the pin; diverge bodies.

How-to vs debit = JSON × Lumen × Pulse / cost = 2 × JSON. On picks 8–10 that
must stay ≤ Earn classic How-to (advertised ×4 → 3000 / 3600 / 4000).

Naming: `easy_buy_classic.py` matches `easy_off_classic.py` + `easy_buy_low.py`.

Scope: **Buy classic only.** Other risks plug in via their own `BuyRiskConfig`.
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
from easy_off_classic import CLASSIC_HUD, CLASSIC_OFF
from keno_pick_one import lumen_placed_on_pick, settled_stats

__all__ = [
    "BUY_COSTS",
    "CLASSIC_BUY_CONFIG",
    "EASY_BUY_CLASSIC",
    "EASY_BUY_CLASSIC_BUY100",
    "EASY_BUY_CLASSIC_PICK1",
    "JSON_MAX_LADDER",
    "JSON_MAX_LADDER_BUY100",
    "ZERO_MASK_BUY100",
    "RTP_WINDOW",
    "ZERO_MASK",
    "cost_row_for",
    "easy_buy_classic_summary",
    "generate_easy_buy_classic",
    "json_max_for",
    "retarget_easy_buy_row",
    "to_json_row",
]

#: JSON (base-bet) advertised max for buy10. NOT pinned to Off classic max.
JSON_MAX_LADDER = {
    2: 4.8,  # hit-or-miss Lumen: 4.8/2.6 is the 0.9650 lattice point
    3: 5.4,
    4: 18.0,  # baseline pick4; medium/high buy10 diverge mid/top from this
    # Pick 5: 75 forced 3.5→75 (~21×). Lower top; Off classic is 75 so buy
    # bonus yields to gradual feel (same tension as buy-low pick 4).
    5: 40.0,  # gradual mid→top (~5–6×); Off classic is 75
    # Pick 6: 320 forced ~16× last catch + mid wall. 200 keeps buy100 legal.
    6: 200.0,
    7: 1200.0,
    8: 1200.0,
    9: 1800.0,
    10: 2000.0,
}

#: Zero mask per pick (True = advertised 0). Deeper than Classic HUD zeros
#: on several picks so last-catch / mid ratios can clear under raised tops.
ZERO_MASK = {
    2: (True, False, False),
    3: (True, False, False, False),
    4: (True, True, False, False, False),
    5: (True, True, True, False, False, False),
    6: (True, True, True, False, False, False, False),
    7: (True, True, True, True, False, False, False, False),
    8: (True, True, True, True, False, False, False, False, False),
    9: (True, True, True, True, True, False, False, False, False, False),
    10: (True, True, True, True, False, False, False, False, False, False, False),
}

#: Shipped Buy `classic` chart for buy10 (picks 2–10), JSON / base-bet units.
EASY_BUY_CLASSIC: dict[int, list[float]] = {
    2: [0.0, 2.6, 4.8],
    3: [0.0, 2.1, 3.9, 5.4],
    4: [0.0, 0.0, 1.2, 14.3, 18.0],
    5: [0.0, 0.0, 0.0, 5.3, 31.7, 40.0],
    6: [0.0, 0.0, 0.0, 1.4, 16.7, 53.1, 200.0],
    7: [0.0, 0.0, 0.0, 0.0, 5.8, 42.5, 128.6, 1200.0],
    8: [0.0, 0.0, 0.0, 0.0, 6.2, 9.8, 80.0, 240.0, 1200.0],
    9: [0.0, 0.0, 0.0, 0.0, 0.0, 15.3, 44.7, 126.9, 360.0, 1800.0],
    10: [0.0, 0.0, 0.0, 0.0, 4.6, 5.9, 10.2, 35.3, 123.0, 399.9, 2000.0],
}

#: buy100 JSON tops — climb to Max Payout pin 450; diverge pick3–10 from buy10.
#: pick2 is the unique RTP-legal row under placed 100× Lumen (same as buy10).
#: Max Payout: keep ABS 90_000 → JSON≤450 / How-to≤900 (3-Star 100k minus margin).
JSON_MAX_LADDER_BUY100 = {
    2: 5.2,
    3: 5.5,
    4: 16.0,  # vs buy10 18
    5: 45.0,
    6: 150.0,
    7: 300.0,
    8: 400.0,
    9: 425.0,
    10: 450.0,  # How-to vs debit = 900
}

ZERO_MASK_BUY100 = {
    9: (True, True, True, False, False, False, False, False, False, False),
}

EASY_BUY_CLASSIC_BUY100: dict[int, list[float]] = {
    2: [0.0, 2.8, 5.2],
    3: [0.0, 2.8, 3.9, 5.5],
    4: [0.0, 0.0, 2.3, 12.7, 16.0],
    5: [0.0, 0.0, 0.0, 5.1, 35.8, 45.0],
    6: [0.0, 0.0, 0.0, 2.4, 19.0, 34.1, 150.0],
    7: [0.0, 0.0, 0.0, 0.0, 6.4, 37.3, 239.9, 300.0],
    8: [0.0, 0.0, 0.0, 0.0, 3.8, 30.0, 39.9, 80.0, 400.0],
    9: [0.0, 0.0, 0.0, 0.9, 3.5, 14.0, 19.9, 68.0, 85.0, 425.0],
    10: [0.0, 0.0, 0.0, 0.0, 2.0, 8.0, 29.1, 40.1, 100.0, 360.0, 450.0],
}

#: pick_1 is chip-specific (not placed; lattice search in solve_paytables).
EASY_BUY_CLASSIC_PICK1: dict[str, list[float]] = {
    "buy10": [1.6, 3.2],
    "buy100": [0.1, 3.7],
}

CLASSIC_BUY_CONFIG = BuyRiskConfig(
    risk="classic",
    json_max_ladder=JSON_MAX_LADDER,
    zero_mask=ZERO_MASK,
    hud=CLASSIC_HUD,
    baked={
        "buy10": EASY_BUY_CLASSIC,
        "buy100": EASY_BUY_CLASSIC_BUY100,
    },
    pick1=EASY_BUY_CLASSIC_PICK1,
    off_chart=CLASSIC_OFF,
    json_max_ladder_buy100=JSON_MAX_LADDER_BUY100,
    zero_mask_buy100=ZERO_MASK_BUY100,
    apply_payout_cap=True,
    # Classic shallow tops already gradual enough without geometric seed;
    # keep share + baked preference so retarget stays stable vs shipped chart.
    use_geometric_seed=True,
    fix_last_catch_on_climb=True,
    neighbour_deltas=(-12, -8, -5, -3, -2, -1, 1, 2, 3, 5, 8, 12),
    transfer_steps=(1, 2, 3, 5, 8, 12, 20),
    climb_guards=150,
    prefer_exact_baked=True,
    buy_bonus_min_pick=6,
    earn_how_to_cap={8: 3000.0, 9: 3600.0, 10: 4000.0},
)


# Back-compat name used by solve_paytables (`json_max_for as classic_buy_json_max_for`).
def json_max_for(k: int, cost: float) -> float:
    """Designed JSON top, floored by the chip's Max Payout pin."""
    return shared_json_max_for(CLASSIC_BUY_CONFIG, k, cost)


def retarget_easy_buy_row(k: int, buy: str = "buy10") -> list[float]:
    """Cost-unit row for pick k on this chip."""
    return retarget_buy_row(CLASSIC_BUY_CONFIG, k, buy)


def generate_easy_buy_classic(buy: str = "buy10") -> dict[int, list[float]]:
    """JSON-unit chart for picks 2–10 on this chip."""
    return generate_buy_chart(CLASSIC_BUY_CONFIG, buy)


def cost_row_for(k: int, buy: str) -> list[float]:
    """Designed row in cost units for the solver."""
    return cost_row_for_cfg(CLASSIC_BUY_CONFIG, k, buy)


def _validate() -> None:
    # Baked charts must be legal under buy settlement; buy10 tops match ladder.
    prev_max = None
    for buy, cost in BUY_COSTS.items():
        chart = EASY_BUY_CLASSIC if buy == "buy10" else EASY_BUY_CLASSIC_BUY100
        for k, row in sorted(chart.items()):
            assert len(row) == k + 1
            from buy_bonus import zero_mask_for as _zmf
            mask = _zmf(CLASSIC_BUY_CONFIG, k, buy)
            assert [m == 0 for m in row] == list(mask), (
                f"{buy} pick_{k}: zero mask diverges from designed mask"
            )
            expected_top = json_max_for(k, cost)
            assert abs(max(row) - expected_top) < 1e-9, (
                f"{buy} pick_{k}: JSON top {max(row)} != designed {expected_top}"
            )
            if buy == "buy10":
                assert max(row) == JSON_MAX_LADDER[k]
                if prev_max is not None:
                    assert max(row) + 1e-9 >= prev_max, (
                        f"pick_{k}: JSON top {max(row)} < pick_{k-1} {prev_max}"
                    )
                prev_max = max(row)
            paying = [m for m in row if m > 0]
            assert all(b > a for a, b in zip(paying, paying[1:]))
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            assert legal(CLASSIC_BUY_CONFIG, k, mask, crow, crow[k], cost, buy), (
                f"{buy} pick_{k}: not legal under buy settlement"
            )
            stats = settled_stats(
                "classic", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            if (
                buy == "buy10"
                and k >= 6
                and JSON_MAX_LADDER[k] > CLASSIC_OFF[k][-1] + 1e-9
            ):
                assert max(row) > CLASSIC_OFF[k][-1] + 1e-9, (
                    f"pick_{k}: JSON top {max(row)} must exceed Off "
                    f"{CLASSIC_OFF[k][-1]} (buy bonus; Off pin lifted)"
                )
            if k >= 8:
                earn_how = {8: 3000.0, 9: 3600.0, 10: 4000.0}[k]
                assert stats["max_m"] <= earn_how + 1e-9, (
                    f"{buy} pick_{k}: vs-debit {stats['max_m']} > Earn How-to {earn_how}"
                )


_validate()


def easy_buy_classic_summary() -> str:
    lines = []
    for buy, cost in BUY_COSTS.items():
        j1 = EASY_BUY_CLASSIC_PICK1[buy]
        crow1 = [m / cost for m in j1]
        s1 = settled_stats(
            "classic", 1, crow1, bought=True, placed=False, cost=cost, buy=buy
        )
        lines.append(
            f"classic_pick_1_{buy} {j1} rtp={s1['rtp']:.6f} "
            f"edge={1 - s1['rtp']:.4%} (lumen hit/miss modeled)"
        )
        chart = EASY_BUY_CLASSIC if buy == "buy10" else EASY_BUY_CLASSIC_BUY100
        for k, row in sorted(chart.items()):
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            stats = settled_stats(
                "classic", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            cells = " / ".join(f"{m:g}" for m in row if m > 0)
            lines.append(
                f"classic_pick_{k:<2d}_{buy} [{cells}] "
                f"rtp={stats['rtp']:.6f} edge={1 - stats['rtp']:.4%} "
                f"hr={stats['hit_rate']:.4f} how={stats['max_m']:.0f} "
                f"placed={int(placed)}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_buy_classic_summary())
