#!/usr/bin/env python3
"""Export published luma-keno LUTs to the web demo.

Reads the actual publish artifacts (library/publish_files/lookUpTable_<mode>_0.csv
plus the segmented criteria file that maps sim id -> hits) and writes
web/src/data/keno-books.json: { mode: [{id, hits, weight, payout}] }.

The web client's RGS stub samples these rows by weight — the same draw the
real RGS performs on /wallet/play. Consistency against the solved paytables is
asserted so the embedded artifact can never drift from the published math.
"""

from __future__ import annotations

import json
import os
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(HERE, "library")
PUBLISH = os.path.join(LIBRARY, "publish_files")
LOOKUPS = os.path.join(LIBRARY, "lookup_tables")
WEB_OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "web", "src", "data", "keno-books.json"))


def export_mode(mode: str, k: int, paytable: list[float]) -> dict:
    lut_path = os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv")
    seg_path = os.path.join(LOOKUPS, f"lookUpTableSegmented_{mode}.csv")

    criteria = {}
    with open(seg_path, encoding="UTF-8") as handle:
        for line in handle:
            sim_id, crit, *_ = line.strip().split(",")
            criteria[sim_id] = int(crit.rsplit("_", 1)[-1])

    rows = []
    with open(lut_path, encoding="UTF-8") as handle:
        for line in handle:
            sim_id, weight, payout = line.strip().split(",")
            hits = criteria[sim_id]
            payout_int = int(payout)
            expected = int(round(paytable[hits] * 100))
            assert payout_int == expected, (
                f"{mode}: LUT payout {payout_int} != paytable[{hits}] {expected}"
            )
            rows.append(
                {
                    "id": int(sim_id),
                    "hits": hits,
                    "weight": int(weight),
                    "payout": payout_int,
                }
            )

    rows.sort(key=lambda r: r["id"])
    assert len(rows) == k + 1, f"{mode}: expected {k + 1} books, found {len(rows)}"

    drawn, pool = 10, 40
    total = sum(r["weight"] for r in rows)
    assert total == comb(pool, k), f"{mode}: weight sum {total} != C({pool},{k})"

    hits_seen = {r["hits"] for r in rows}
    assert hits_seen == set(range(k + 1)), f"{mode}: missing hit rows"

    for r in rows:
        expect = comb(drawn, r["hits"]) * comb(pool - drawn, k - r["hits"])
        assert r["weight"] == expect, (
            f"{mode} hits={r['hits']}: weight {r['weight']} != {expect}"
        )

    return {
        "cost": 1.0,
        "rtp": sum(r["weight"] * r["payout"] for r in rows) / (comb(pool, k) * 100),
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
            modes[mode] = export_mode(mode, k, row)

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
    print(f"{len(modes)} modes; RTP {min(rtps):.4f}-{max(rtps):.4f}; all weights exact")


if __name__ == "__main__":
    main()
