"""Export one chart's paytable + books to the web client, one section at a time.

    python3 export_chart.py risks medium 10      # Off medium, pick 10 lock-checked
    python3 export_chart.py earn classic 10
    python3 export_chart.py buy100 medium 10

Replaces the per-section `export_*_books.py` scripts, which each hardcoded the
container path `/workspace` and one risk. Books are rebuilt from the paytable
rather than patched in place: the payout column has to agree with the booked
weight, and editing one without the other is how the two drift.

The trailing pick arguments are the picks that must clear `shape_lock` before
anything is written. Passing none exports the section without a lock check,
which is correct for a section whose columns have not been restaired yet.
"""

from __future__ import annotations

import json
import os
import sys
from math import comb

from keno_pick_one import (
    BUY_SUFFIXES,
    POOL,
    REASON_TO_EVENT,
    book_count_for_picks,
    lumen_boost_applied,
    lumen_placed_on_pick,
    off_outcomes,
    off_pay,
    off_weight,
    paying_from_table,
    pulse_boost_applied,
    settle_pay,
    spin_outcomes,
    spin_weight,
    weight_total,
)
from shape_lock import describe, lock_for, violations
from shape_report import grade
from web_paths import resolve_web_file

HERE = os.path.dirname(os.path.abspath(__file__))
SECTIONS = ("risks", "earn", "buy10", "buy100")


def mode_name(section: str, risk: str, k: int) -> str:
    if section == "risks":
        return f"{risk}_pick_{k}"
    if section == "earn":
        return f"{risk}_pick_{k}_earn"
    return f"{risk}_pick_{k}_{section}"


def export_off(k: int, risk: str, paytable: list[float]) -> dict:
    rows = []
    for i, spin in enumerate(off_outcomes(k, risk)):
        rows.append(
            {
                "id": i,
                "hits": spin.main_hits,
                "mainHits": spin.main_hits,
                "lumenHit": False,
                "lumenBoost": 1.0,
                "extrasOpened": False,
                "extraHits": 0,
                "extraReason": None,
                "pulse": 1.0,
                "pulseRolled": False,
                "missBonus": bool(spin.miss_bonus),
                "weight": int(off_weight(k, spin, risk)),
                "payout": int(round(off_pay(spin, paytable) * 100)),
            }
        )
    total = sum(r["weight"] for r in rows)
    assert total == comb(POOL, k), f"pick_{k} weight {total} != {comb(POOL, k)}"
    return {"cost": 1.0, "rtp": sum(r["weight"] * r["payout"] for r in rows) / (total * 100), "books": rows}


def export_settled(
    k: int, risk: str, paytable: list[float], cost: float, buy: str | None
) -> dict:
    bought = buy is not None
    placed = lumen_placed_on_pick(buy, k) if bought else False
    paying = paying_from_table(paytable)
    rows = []
    for i, spin in enumerate(
        spin_outcomes(k, paying=paying, bought=bought, placed=placed)
    ):
        base = paytable[spin.total_hits]
        rows.append(
            {
                "id": i,
                "hits": spin.total_hits,
                "mainHits": spin.main_hits,
                "lumenHit": spin.lumen_hit,
                "lumenBoost": lumen_boost_applied(base, spin.lumen_hit, risk, buy),
                "extrasOpened": spin.extras,
                "extraHits": spin.extra_hits if spin.extras else 0,
                "extraReason": REASON_TO_EVENT[spin.extra_reason],
                "pulse": pulse_boost_applied(
                    settle_pay(base, spin.lumen_hit, False, risk, buy), spin.pulse, risk
                ),
                "pulseRolled": bool(spin.pulse),
                "missBonus": bool(spin.miss_bonus),
                "weight": int(
                    spin_weight(k, spin, risk, paying=paying, bought=bought, placed=placed)
                ),
                "payout": int(
                    round(settle_pay(base, spin.lumen_hit, spin.pulse, risk, buy) * 100)
                ),
            }
        )
    total = sum(r["weight"] for r in rows)
    expect = weight_total(k, placed=placed)
    assert total == expect, f"pick_{k} weight {total} != {expect}"
    expect_n = book_count_for_picks(k, 10, paying, bought, placed)
    assert len(rows) == expect_n, f"pick_{k}: {len(rows)} books != {expect_n}"
    return {
        "cost": cost,
        # Payouts are base-stake multiples, so a buy round divides by what the
        # player actually spent before the number is called an RTP.
        "rtp": sum(r["weight"] * r["payout"] for r in rows) / (total * 100 * cost),
        "books": rows,
    }


def main(section: str, risk: str, locked: set[int]) -> None:
    if section not in SECTIONS:
        raise SystemExit(f"section must be one of {SECTIONS}")
    doc = json.load(open(os.path.join(HERE, "paytables.json"), encoding="UTF-8"))
    pay_path = resolve_web_file("keno-paytables.json", "KENO_WEB_PAYTABLES")
    books_path = resolve_web_file("keno-books.json", "KENO_WEB_BOOKS")
    front = json.load(open(pay_path, encoding="UTF-8"))
    books = json.load(open(books_path, encoding="UTF-8"))

    tables = doc[section][risk]
    cost = BUY_SUFFIXES.get(section, 1.0) if section in BUY_SUFFIXES else 1.0
    buy = section if section in BUY_SUFFIXES else None

    # Gate every locked pick before touching the client: a half-written export
    # is worse than a late one.
    for k in sorted(locked):
        row, coeff, _stats, unit = grade(section, risk, k, tables[str(k)])
        errs = violations(row, k, lock=lock_for(unit), label=mode_name(section, risk, k))
        if errs:
            raise SystemExit("shape lock: " + "; ".join(errs))

    front.setdefault(section, {})[risk] = tables
    for k_s, row in sorted(tables.items(), key=lambda t: int(t[0])):
        k = int(k_s)
        name = mode_name(section, risk, k)
        mode = (
            export_off(k, risk, row)
            if section == "risks"
            else export_settled(k, risk, row, cost, buy)
        )
        books["modes"][name] = mode
        how_to = max(r["payout"] for r in mode["books"]) / 100
        mark = "  shape-locked" if k in locked else ""
        print(
            f"{name:22s} rtp={mode['rtp']:.6f} books={len(mode['books']):4d} "
            f"how_to={how_to:g}x{mark}"
        )
        if k in locked:
            g_row, coeff, _s, unit = grade(section, risk, k, row)
            print(f"{'':22s} {describe(coeff, g_row, k, lock=lock_for(unit))}")

    for path, payload in ((pay_path, front), (books_path, books)):
        with open(path, "w", encoding="UTF-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], {int(a) for a in sys.argv[3:]})
