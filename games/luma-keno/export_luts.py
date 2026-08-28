#!/usr/bin/env python3
"""Export published luma-keno LUTs to the web demo.

Off modes are table-only. Earn modes include lumenHit, extras, and lumenBoost.
"""

from __future__ import annotations

import json
import os
from math import comb

from keno_pick_one import (
    BUY_SUFFIXES,
    REASON_TO_EVENT,
    book_count_for_picks,
    off_outcomes,
    off_pay,
    off_weight,
    lumen_boost_applied,
    pulse_boost_applied,
    parse_spin_criteria,
    paying_from_table,
    settle_pay,
    spin_weight,
    weight_scale,
)
from web_paths import resolve_web_file

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(HERE, "library")
PUBLISH = os.path.join(LIBRARY, "publish_files")
LOOKUPS = os.path.join(LIBRARY, "lookup_tables")
DRAWN = 10
POOL = 40


def resolve_web_out() -> str:
    return resolve_web_file("keno-books.json", "KENO_WEB_BOOKS")


def export_mode(
    mode: str,
    k: int,
    risk: str,
    paytable: list[float],
    earn: bool,
    cost: float = 1.0,
    bought: bool = False,
) -> dict:
    lut_path = os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv")
    seg_path = os.path.join(LOOKUPS, f"lookUpTableSegmented_{mode}.csv")

    criteria = {}
    with open(seg_path, encoding="UTF-8") as handle:
        for line in handle:
            sim_id, crit, *_ = line.strip().split(",")
            criteria[sim_id] = crit

    rows = []
    with open(lut_path, encoding="UTF-8") as handle:
        for line in handle:
            sim_id, weight, payout = line.strip().split(",")
            spin = parse_spin_criteria(criteria[sim_id])
            payout_int = int(payout)
            if earn:
                paying = paying_from_table(paytable)
                base = paytable[spin.total_hits]
                expected = int(round(settle_pay(base, spin.lumen_hit, spin.pulse, risk) * 100))
                expect_weight = spin_weight(
                    k, spin, risk, paying=paying, bought=bought
                )
                after_lumen = lumen_boost_applied(base, spin.lumen_hit, risk)
            else:
                base = off_pay(spin, paytable)
                expected = int(round(base * 100))
                expect_weight = off_weight(k, spin)
                after_lumen = 1.0
            assert payout_int == expected, (
                f"{mode}: LUT payout {payout_int} != settle {expected} "
                f"(hits={spin.total_hits} lumen={spin.lumen_hit} pulse={spin.pulse})"
            )
            assert int(weight) == expect_weight, (
                f"{mode} {criteria[sim_id]}: weight {weight} != {expect_weight}"
            )
            rows.append(
                {
                    "id": int(sim_id),
                    "hits": spin.total_hits if earn else spin.main_hits,
                    "mainHits": spin.main_hits,
                    "lumenHit": spin.lumen_hit if earn else False,
                    "lumenBoost": after_lumen if earn else 1.0,
                    "extrasOpened": spin.extras if earn else False,
                    "extraHits": spin.extra_hits if earn and spin.extras else 0,
                    "extraReason": REASON_TO_EVENT[spin.extra_reason] if earn else None,
                    "pulse": pulse_boost_applied(
                        settle_pay(base, spin.lumen_hit, False, risk), spin.pulse, risk
                    )
                    if earn
                    else 1.0,
                    # `pulse` is the boost Pulse managed to apply, which collapses
                    # to 1.0 on a 0x row. Without this flag a wasted Pulse roll is
                    # indistinguishable from no roll at all, so the client cannot
                    # render it and the impression rate cannot be measured.
                    "pulseRolled": bool(spin.pulse) if earn else False,
                    # Off pick_1 only: this miss pays the advertised bonus amount
                    # rather than the plain one. The client needs it to label the
                    # row, since both amounts sit on the same hit count.
                    "missBonus": bool(spin.miss_bonus),
                    "weight": int(weight),
                    "payout": payout_int,
                }
            )

    rows.sort(key=lambda r: r["id"])
    expect_n = (
        book_count_for_picks(k, DRAWN, paying_from_table(paytable), bought)
        if earn
        else len(off_outcomes(k))
    )
    assert len(rows) == expect_n, f"{mode}: expected {expect_n} books, found {len(rows)}"

    total = sum(r["weight"] for r in rows)
    expect_total = comb(POOL, k) * DRAWN * weight_scale() if earn else comb(POOL, k)
    assert total == expect_total, f"{mode}: weight sum {total} != {expect_total}"

    return {
        "cost": cost,
        # Payouts are base-stake multiples in hundredths, so a buy round divides
        # by its cost to report the return on what the player actually spent.
        "rtp": sum(r["weight"] * r["payout"] for r in rows) / (total * 100 * cost),
        "books": rows,
    }


def carry_unpublished(web_out: str, modes: dict[str, dict]) -> list[str]:
    """Keep modes the client already ships that this build does not generate.

    The buy chips are UI-only: they live in the web LUTs but have no paytable or
    BetMode here. Dropping them would leave the client throwing `unknown mode`,
    so they are carried forward and reported on every export rather than being
    quietly deleted or quietly kept.
    """
    if not os.path.isfile(web_out):
        return []
    with open(web_out, encoding="UTF-8") as handle:
        existing = json.load(handle).get("modes", {})
    carried = [name for name in existing if name not in modes]
    for name in carried:
        modes[name] = existing[name]
    return carried


def main() -> None:
    with open(os.path.join(HERE, "paytables.json"), encoding="UTF-8") as handle:
        paytables = json.load(handle)

    modes: dict[str, dict] = {}
    for risk, tables in paytables["risks"].items():
        for k_s, row in tables.items():
            k = int(k_s)
            mode = f"{risk}_pick_{k}"
            modes[mode] = export_mode(mode, k, risk, row, False)
    for risk, tables in paytables["earn"].items():
        for k_s, row in tables.items():
            k = int(k_s)
            mode = f"{risk}_pick_{k}_earn"
            modes[mode] = export_mode(mode, k, risk, row, True)
    for buy, cost in BUY_SUFFIXES.items():
        for risk, tables in paytables[buy].items():
            for k_s, row in tables.items():
                k = int(k_s)
                mode = f"{risk}_pick_{k}_{buy}"
                modes[mode] = export_mode(mode, k, risk, row, True, cost, True)

    doc = {
        "gameId": "luma-keno",
        "pool": paytables["pool"],
        "drawn": paytables["drawn"],
        "modes": modes,
    }
    web_out = resolve_web_out()
    carried = carry_unpublished(web_out, modes)
    with open(web_out, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")

    rtps = [m["rtp"] for m in modes.values()]
    print(f"wrote {web_out}")
    print(f"{len(modes)} modes; RTP {min(rtps):.4f}-{max(rtps):.4f}")
    if carried:
        print(
            f"WARNING: carried {len(carried)} mode(s) this build does not produce: "
            f"{', '.join(sorted(carried)[:4])}"
            f"{' …' if len(carried) > 4 else ''}\n"
            "  They are shipping to players without certified math behind them.\n"
            "  Either add them to paytables.json and the BetMode list, or remove\n"
            "  them from the client."
        )


if __name__ == "__main__":
    main()
