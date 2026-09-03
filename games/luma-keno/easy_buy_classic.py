"""Buy `classic` — thin risk wrapper over `buy_bonus`.

Off `classic` (`easy_off_classic.py`) is a max-anchored geometric HUD. Buy
chips use the shared buy-bonus leftover/lock path (`buy_bonus.py`) with
classic-specific tops, zero masks, and Max Payout flooring on buy100.

Hierarchy: the app advertises a strict risk ladder `low < classic < medium <
high`. Buy10 `classic` tops are the **geometric midpoint** between buy10
`low` and buy10 `medium` per pick (√(low×medium)), so classic sits between
them on every pick where the Lumen lattice leaves room (picks 4, 6–10).
Picks 2/3 use distinct window points (low 3.6/5.1 < classic 4.8/5.6 <
medium 6.5/7.1). Pick 5 is still lattice-pinned (low == medium == 40).
This deliberately drops buy10 classic BELOW Off classic on picks 6–10
(Off classic is itself above medium buy10 there), relaxing the old
"buy bonus must exceed Off" contract in favour of the product hierarchy.
Buy10 classic still carries MORE multipliers than buy10 low on every pick
(2–10 except the pick-5 pin) — the "same easy logic, more multipliers" brief.

buy100 keeps its own ladder (JSON_MAX_LADDER_BUY100) floored by the Max
Payout pin 450 (MAX_PAYOUT_ABS[100]=90_000, 3-Star 100k − margin); buy100
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

#: JSON (base-bet) advertised max for buy10. Hierarchy-driven: geometric
#: midpoint √(buy10_low × buy10_medium) per pick, so classic sits between low
#: and medium. Picks 2/3 are distinct window points (not shared with Easy).
#: Pick 5 is still lattice-pinned (low == medium == 40). Classic still
#: exceeds buy10 low on every pick — more multipliers.
JSON_MAX_LADDER = {
    2: 4.8,  # 2.3/4.8 = 0.9644; above Easy 3.6, below medium 6.5
    3: 5.6,  # 2.1/3.7/5.6 = 0.9651; above Easy 5.1, below medium 7.1
    4: 9.8,  # √(low 8 × medium 12)
    5: 40.0,  # lattice-pinned (low == medium == 40)
    6: 94.9,  # √(low 60 × medium 150)
    7: 219.1,  # √(low 120 × medium 400)
    8: 357.8,  # √(low 160 × medium 800)
    9: 536.7,  # √(low 180 × medium 1600)
    10: 632.5,  # √(low 200 × medium 2000)
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
#: Hierarchy-driven tops (geometric mid between buy10 low and medium); bodies
#: solved by the shared buy-bonus solver onto ~0.9650 with shape_lock + ETL
#: + hit-rate gates. Same easy/low logic (gradual geometric mid→top), more
#: multipliers than low, below medium.
EASY_BUY_CLASSIC: dict[int, list[float]] = {
    2: [0.0, 2.3, 4.8],
    3: [0.0, 1.6, 4.4, 5.6],
    4: [0.0, 0.0, 3.7, 7.7, 9.8],
    5: [0.0, 0.0, 0.0, 5.2, 31.7, 40.0],
    6: [0.0, 0.0, 0.0, 2.3, 14.8, 51.5, 94.9],
    7: [0.0, 0.0, 0.0, 0.0, 9.9, 30.4, 99.1, 219.1],
    8: [0.0, 0.0, 0.0, 0.0, 8.9, 11.2, 28.5, 71.5, 357.8],
    9: [0.0, 0.0, 0.0, 0.0, 0.0, 21.6, 22.2, 84.8, 107.3, 536.7],
    10: [0.0, 0.0, 0.0, 0.0, 4.8, 6.8, 9.7, 15.5, 45.1, 126.5, 632.5],
}

#: buy100 JSON tops — hierarchy-driven: classic = √(low × medium) per pick
#: (geometric mid between buy100 low and the new buy100 medium = high/1.5).
#: Picks 2/3 lattice-pinned (== low == medium == high). Below medium, above low.
JSON_MAX_LADDER_BUY100 = {
    2: 5.2,
    3: 5.5,
    4: 12.3,  # √(low 9 × medium 16.7)
    5: 43.2,  # √(low 40 × medium 46.7)
    6: 148.8,  # √(low 80 × medium 276.7)
    7: 201.5,  # √(low 145 × medium 280)
    8: 236.6,  # √(low 200 × medium 280)
    9: 236.6,  # √(low 200 × medium 280)
    10: 244.9,  # √(low 200 × medium 300)
}

ZERO_MASK_BUY100 = {
    9: (True, True, True, False, False, False, False, False, False, False),
}

EASY_BUY_CLASSIC_BUY100: dict[int, list[float]] = {
    2: [0.0, 2.4, 5.2],
    3: [0.0, 2.4, 4.2, 5.5],
    4: [0.0, 0.0, 3.5, 9.6, 12.3],
    5: [0.0, 0.0, 0.0, 5.3, 34.5, 43.2],
    6: [0.0, 0.0, 0.0, 2.4, 18.9, 33.4, 148.8],
    7: [0.0, 0.0, 0.0, 0.0, 11.1, 25.2, 161.2, 201.5],
    8: [0.0, 0.0, 0.0, 0.0, 4.0, 30.2, 37.8, 47.3, 236.6],
    9: [0.0, 0.0, 0.0, 2.0, 3.7, 8.6, 30.2, 37.8, 47.3, 236.6],
    10: [0.0, 0.0, 0.0, 0.0, 3.5, 7.0, 24.9, 31.2, 39.1, 48.9, 244.9],
}

#: pick_1 is chip-specific (not placed; lattice search in solve_paytables).
EASY_BUY_CLASSIC_PICK1: dict[str, list[float]] = {
    "buy10": [0.4, 3.0],
    "buy100": [0.4, 3.0],  # 7% Pulse; 4% has no in-band pair after extra-cover
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
            if buy == "buy10" and k in (2, 3):
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


    from easy_buy_high import JSON_MAX_LADDER as HIGH_MAX
    from easy_buy_low import JSON_MAX_LADDER as LOW_MAX
    from easy_buy_medium import JSON_MAX_LADDER as MEDIUM_MAX

    for k in (2, 3):
        tops = (LOW_MAX[k], JSON_MAX_LADDER[k], MEDIUM_MAX[k], HIGH_MAX[k])
        assert tops[0] < tops[1] < tops[2] < tops[3], (
            f"buy10 pick_{k} maxes {tops} are not low < classic < medium < high"
        )


_validate()


def easy_buy_classic_summary() -> str:
    lines = []
    for buy, cost in BUY_COSTS.items():
        j1 = EASY_BUY_CLASSIC_PICK1[buy]
        crow1 = [m / cost for m in j1]
        s1 = settled_stats(
            "classic", 1, crow1, bought=True, placed=True, cost=cost, buy=buy
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
