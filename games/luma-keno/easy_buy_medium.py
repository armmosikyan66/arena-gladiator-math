"""Buy `medium` — thin risk wrapper over `buy_bonus`.

Off `medium` (`easy_off_medium.py`) is a max-anchored geometric HUD. Buy
chips use the shared buy-bonus leftover/lock path (`buy_bonus.py`) with
medium-specific tops and zero masks. Placed Lumen + Pulse eat RTP on early
hits, so JSON tops sit well under Off medium — prefer gradual hit-to-hit
steps over clearing Off (same tension as buy-low pick 4).

How-to vs debit = JSON × Lumen × Pulse / cost = 2 × JSON. Deep picks stay
≤ Earn medium How-to and the dashboard Max Payout pin (buy10 JSON ≤ 2250;
buy100 JSON ≤ 450 from ABS 90_000 — keep that pin; How-to ceiling = 900).

Scope: **Buy medium only.** buy100 uses a separate JSON_MAX ladder + baked
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
from easy_off_medium import MEDIUM_OFF
from keno_pick_one import lumen_placed_on_pick, settled_stats

__all__ = [
    "BUY_COSTS",
    "EASY_BUY_MEDIUM",
    "EASY_BUY_MEDIUM_BUY100",
    "EASY_BUY_MEDIUM_PICK1",
    "JSON_MAX_LADDER",
    "JSON_MAX_LADDER_BUY100",
    "MEDIUM_BUY_CONFIG",
    "RTP_WINDOW",
    "ZERO_MASK",
    "ZERO_MASK_BUY100",
    "cost_row_for",
    "easy_buy_medium_summary",
    "generate_easy_buy_medium",
    "json_max_for",
    "retarget_easy_buy_row",
    "to_json_row",
]

#: JSON (base-bet) advertised max for buy10. NOT pinned to Off medium max.
#: Climbing, gradual mid→top (max adjacent paying ratio ~≤10× on deep cards).
JSON_MAX_LADDER = {
    2: 4.8,  # hit-or-miss Lumen: 4.8/2.6 is the 0.9650 lattice point
    3: 5.4,
    4: 12.0,  # diverge vs classic 18: higher mid body / lower top
    5: 40.0,
    6: 150.0,  # Off 650 forced a 3.7→650 cliff; gradual body under placed Lumen
    7: 400.0,
    8: 800.0,  # under Max Payout JSON 2250
    9: 1600.0,
    10: 2000.0,
}

#: Zero mask per pick (True = advertised 0). Deeper than Medium HUD on several
#: picks so last-catch / mid ratios clear under raised buy tops.
ZERO_MASK = {
    2: (True, False, False),
    3: (True, False, False, False),
    4: (True, True, False, False, False),
    5: (True, True, True, False, False, False),
    6: (True, True, True, False, False, False, False),
    7: (True, True, True, False, False, False, False, False),
    8: (True, True, True, True, False, False, False, False, False),
    9: (True, True, True, False, False, False, False, False, False, False),
    10: (True, True, True, False, False, False, False, False, False, False, False),
}

#: Shipped Buy `medium` chart for buy10 (picks 2–10), JSON / base-bet units.
EASY_BUY_MEDIUM: dict[int, list[float]] = {
    2: [0.0, 2.6, 4.8],
    3: [0.0, 2.1, 3.9, 5.4],
    4: [0.0, 0.0, 3.1, 9.4, 12.0],
    5: [0.0, 0.0, 0.0, 5.3, 31.7, 40.0],
    6: [0.0, 0.0, 0.0, 1.7, 16.0, 54.0, 150.0],
    7: [0.0, 0.0, 0.0, 1.2, 5.1, 37.9, 114.6, 400.0],
    8: [0.0, 0.0, 0.0, 0.0, 7.9, 10.0, 50.2, 160.0, 800.0],
    9: [0.0, 0.0, 0.0, 1.1, 3.8, 9.9, 16.7, 57.7, 200.0, 1600.0],
    10: [0.0, 0.0, 0.0, 1.5, 2.4, 6.4, 11.4, 38.7, 133.3, 399.9, 2000.0],
}

#: buy100 JSON tops — deep picks pin at Max Payout (JSON≤450 / How≤900).
#: Mid tops raised under RTP 0.965 / shape_lock; vs-debit How stays < buy10
#: by 3-Star ABS 90k design (buy10 How 4000 cannot be matched without >3-Star).
JSON_MAX_LADDER_BUY100 = {
    2: 5.2,
    3: 5.5,
    4: 11.0,  # vs buy10 12; ≠ high buy100 25
    5: 42.0,  # diverge vs buy10 40
    6: 150.0,
    7: 250.0,
    8: 450.0,  # Max Payout pin
    9: 450.0,  # Max Payout pin
    10: 450.0,  # Max Payout pin; How-to vs debit = 900
}

#: buy100 opens hit-3 on pick10 so RTP clears at the 450 Max Payout pin.
ZERO_MASK_BUY100 = {
    10: (True, True, True, False, False, False, False, False, False, False, False),
}

#: Shipped Buy `medium` chart for buy100 (picks 2–10). Deep tops pin at 450;
#: bodies diverge from buy10 (re-solved mid cells under 100× Lumen).
EASY_BUY_MEDIUM_BUY100: dict[int, list[float]] = {
    2: [0.0, 2.8, 5.2],
    3: [0.0, 2.8, 3.9, 5.5],
    4: [0.0, 0.0, 4.0, 8.6, 11.0],
    5: [0.0, 0.0, 0.0, 5.7, 33.3, 42.0],
    6: [0.0, 0.0, 0.0, 2.4, 19.0, 34.1, 150.0],
    7: [0.0, 0.0, 0.0, 2.3, 4.0, 31.1, 200.0, 250.0],
    8: [0.0, 0.0, 0.0, 0.0, 7.2, 11.4, 68.5, 360.0, 450.0],
    9: [0.0, 0.0, 0.0, 0.4, 2.0, 10.8, 55.5, 70.0, 360.0, 450.0],
    10: [0.0, 0.0, 0.0, 0.8, 2.8, 9.4, 12.5, 45.0, 100.0, 360.0, 450.0],
}

#: pick_1 is chip-specific (not placed; lattice search in solve_paytables).
EASY_BUY_MEDIUM_PICK1: dict[str, list[float]] = {
    "buy10": [2.1, 2.8],
    "buy100": [1.4, 3.4],
}

#: Uniform HUD weights for share seeding (zeros follow ZERO_MASK).
_MEDIUM_BUY_HUD = {
    k: [0.0 if ZERO_MASK[k][h] else 1.0 for h in range(k + 1)]
    for k in ZERO_MASK
}

MEDIUM_BUY_CONFIG = BuyRiskConfig(
    risk="medium",
    json_max_ladder=JSON_MAX_LADDER,
    zero_mask=ZERO_MASK,
    hud=_MEDIUM_BUY_HUD,
    baked={"buy10": EASY_BUY_MEDIUM, "buy100": EASY_BUY_MEDIUM_BUY100},
    pick1=EASY_BUY_MEDIUM_PICK1,
    off_chart=MEDIUM_OFF,
    json_max_ladder_buy100=JSON_MAX_LADDER_BUY100,
    zero_mask_buy100=ZERO_MASK_BUY100,
    apply_payout_cap=True,
    use_geometric_seed=True,
    fix_last_catch_on_climb=True,
    neighbour_deltas=(-12, -8, -5, -3, -2, -1, 1, 2, 3, 5, 8, 12),
    transfer_steps=(1, 2, 3, 5, 8, 12, 20),
    climb_guards=200,
    prefer_exact_baked=True,
    buy_bonus_min_pick=None,  # tops sit under Off by design (gradual)
    earn_how_to_cap={8: 8000.0, 9: 12000.0, 10: 16000.0},
)


def json_max_for(k: int, cost: float) -> float:
    return shared_json_max_for(MEDIUM_BUY_CONFIG, k, cost)


def retarget_easy_buy_row(k: int, buy: str = "buy10") -> list[float]:
    return retarget_buy_row(MEDIUM_BUY_CONFIG, k, buy)


def generate_easy_buy_medium(buy: str = "buy10") -> dict[int, list[float]]:
    return generate_buy_chart(MEDIUM_BUY_CONFIG, buy)


def cost_row_for(k: int, buy: str) -> list[float]:
    return cost_row_for_cfg(MEDIUM_BUY_CONFIG, k, buy)


def _validate() -> None:
    from buy_bonus import zero_mask_for

    for buy, chart in (("buy10", EASY_BUY_MEDIUM), ("buy100", EASY_BUY_MEDIUM_BUY100)):
        cost = BUY_COSTS[buy]
        generated = generate_easy_buy_medium(buy)
        prev_max = None
        for k, row in sorted(chart.items()):
            assert row == generated[k], (
                f"{buy} pick_{k}: baked {row} != generator {generated[k]}"
            )
            assert len(row) == k + 1
            mask = zero_mask_for(MEDIUM_BUY_CONFIG, k, buy)
            assert [m == 0 for m in row] == list(mask), (
                f"{buy} pick_{k}: zero mask diverges from designed mask"
            )
            expected_top = json_max_for(k, cost)
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
            assert legal(MEDIUM_BUY_CONFIG, k, mask, crow, crow[k], cost, buy), (
                f"{buy} pick_{k}: not legal under buy settlement"
            )
            stats = settled_stats(
                "medium", k, crow, bought=True, placed=True, cost=cost, buy=buy
            )
            if k >= 8:
                earn_how = MEDIUM_BUY_CONFIG.earn_how_to_cap[k]
                assert stats["max_m"] <= earn_how + 1e-9, (
                    f"{buy} pick_{k}: vs-debit {stats['max_m']} > Earn How-to {earn_how}"
                )


_validate()


def easy_buy_medium_summary() -> str:
    lines = []
    for buy, cost in BUY_COSTS.items():
        j1 = EASY_BUY_MEDIUM_PICK1[buy]
        crow1 = [m / cost for m in j1]
        s1 = settled_stats(
            "medium", 1, crow1, bought=True, placed=False, cost=cost, buy=buy
        )
        lines.append(
            f"medium_pick_1_{buy} {j1} rtp={s1['rtp']:.6f} "
            f"edge={1 - s1['rtp']:.4%} (lumen hit/miss modeled)"
        )
        chart = EASY_BUY_MEDIUM if buy == "buy10" else EASY_BUY_MEDIUM_BUY100
        for k, row in sorted(chart.items()):
            crow = [m / cost for m in row]
            placed = lumen_placed_on_pick(buy, k)
            stats = settled_stats(
                "medium", k, crow, bought=True, placed=placed, cost=cost, buy=buy
            )
            cells = " / ".join(f"{m:g}" for m in row if m > 0)
            lines.append(
                f"medium_pick_{k:<2d}_{buy} [{cells}] "
                f"rtp={stats['rtp']:.6f} edge={1 - stats['rtp']:.4%} "
                f"hr={stats['hit_rate']:.4f} how={stats['max_m']:.0f} "
                f"placed={int(placed)}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_buy_medium_summary())
