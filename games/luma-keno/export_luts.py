#!/usr/bin/env python3
"""Export published luma-keno LUTs to the web demo.

Off modes are table-only. Earn modes include lumenHit, extras, and lumenBoost.
"""

from __future__ import annotations

import json
import os
from math import comb

from keno_pick_one import (
    REASON_TO_EVENT,
    base_hit_weight,
    book_count_for_picks,
    lumen_boost_applied,
    pulse_boost_applied,
    parse_spin_criteria,
    settle_pay,
    spin_weight,
    weight_scale,
)

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(HERE, "library")
PUBLISH = os.path.join(LIBRARY, "publish_files")
LOOKUPS = os.path.join(LIBRARY, "lookup_tables")
WEB_OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "web", "src", "data", "keno-books.json"))
DRAWN = 10
POOL = 40


def export_mode(mode: str, k: int, risk: str, paytable: list[float], earn: bool) -> dict:
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
                base = paytable[spin.total_hits]
                expected = int(round(settle_pay(base, spin.lumen_hit, spin.pulse, risk) * 100))
                expect_weight = spin_weight(k, spin, risk)
                after_lumen = lumen_boost_applied(base, spin.lumen_hit, risk)
            else:
                base = paytable[spin.main_hits]
                expected = int(round(base * 100))
                expect_weight = base_hit_weight(k, spin.main_hits)
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
                        settle_pay(base, spin.lumen_hit, False, risk), spin.pulse
                    )
                    if earn
                    else 1.0,
                    "weight": int(weight),
                    "payout": payout_int,
                }
            )

    rows.sort(key=lambda r: r["id"])
    expect_n = book_count_for_picks(k, DRAWN) if earn else k + 1
    assert len(rows) == expect_n, f"{mode}: expected {expect_n} books, found {len(rows)}"

    total = sum(r["weight"] for r in rows)
    expect_total = comb(POOL, k) * DRAWN * weight_scale() if earn else comb(POOL, k)
    assert total == expect_total, f"{mode}: weight sum {total} != {expect_total}"

    return {
        "cost": 1.0,
        "rtp": sum(r["weight"] * r["payout"] for r in rows) / (total * 100),
        "books": rows,
    }


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

    doc = {
        "gameId": "luma-keno",
        "pool": paytables["pool"],
        "drawn": paytables["drawn"],
        "modes": modes,
    }
    os.makedirs(os.path.dirname(WEB_OUT), exist_ok=True)
    with open(WEB_OUT, "w", encoding="UTF-8") as handle:
        json.dump(doc, handle, indent=2)

    rtps = [m["rtp"] for m in modes.values()]
    print(f"wrote {WEB_OUT}")
    print(f"{len(modes)} modes; RTP {min(rtps):.4f}-{max(rtps):.4f}")


if __name__ == "__main__":
    main()
