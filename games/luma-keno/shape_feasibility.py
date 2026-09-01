"""What top can each chart carry once the shape lock is enforced?

For every row of interest this prints the frozen top, the band of RTP a
lock-clean ladder can reach with that top, and - when the designed window is
out of reach - the top that would bring it back. Read-only.
"""

from __future__ import annotations

import json
import os

from shape_lock import feasible_rtp_range, lock_for, paying_hits, solve_row
from shape_report import RTP_WINDOW, grade

HERE = os.path.dirname(os.path.abspath(__file__))

ROWS = [
    ("risks", "medium", 10, "1  Off medium 10"),
    ("earn", "low", 10, "2  Earn low 10"),
    ("earn", "classic", 10, "3  Earn classic 10"),
    ("buy100", "medium", 10, "4  Buy100 medium 10"),
    ("risks", "high", 8, "5a Off high 8"),
    ("risks", "high", 9, "5b Off high 9"),
    ("risks", "high", 6, "6  Off high 6"),
    ("risks", "high", 10, "-- Off high 10 (frozen)"),
    ("risks", "classic", 10, "-- Off classic 10 (frozen)"),
    ("risks", "low", 10, "-- Off low 10 (called clean)"),
]


def main() -> None:
    doc = json.load(open(os.path.join(HERE, "paytables.json"), encoding="UTF-8"))
    lo_w, hi_w = RTP_WINDOW
    print(
        f"{'chart':28s} {'top':>10s} {'reachable RTP band':>24s} "
        f"{'verdict':>12s} {'top the lock admits':>22s}"
    )
    print("-" * 102)
    for section, risk, k, label in ROWS:
        json_row = doc[section][risk][str(k)]
        row, coeff, _stats, cost = grade(section, risk, k, json_row)
        lock = lock_for(cost)
        hits = paying_hits(row)
        top = max(row)
        lo, hi = feasible_rtp_range(coeff, hits, top, lock=lock)
        json_top = top * cost

        if lo > hi_w:
            verdict = "TOP TOO HIGH"
            # RTP scales linearly with the whole ladder, so the admissible top
            # scales by the same factor.
            fix = f"cut to <= {json_top * hi_w / lo:,.0f}x"
        elif hi < lo_w:
            verdict = "TOP TOO LOW"
            fix = f"raise to >= {json_top * lo_w / hi:,.0f}x"
        else:
            verdict = "ok"
            fix = "keep"
        print(
            f"{label:28s} {json_top:10,.1f} {lo:>11.4f}..{hi:<11.4f} "
            f"{verdict:>12s} {fix:>22s}"
        )

    print("\nsolver check on the rows whose frozen top is admissible:")
    for section, risk, k, label in ROWS:
        json_row = doc[section][risk][str(k)]
        row, coeff, _stats, cost = grade(section, risk, k, json_row)
        lock = lock_for(cost)
        hits = paying_hits(row)
        top = max(row)
        lo, hi = feasible_rtp_range(coeff, hits, top, lock=lock)
        if lo > hi_w or hi < lo_w:
            continue
        found = solve_row(coeff, k, hits, top, RTP_WINDOW, lock=lock)
        if found is None:
            print(f"  {label:28s} band ok but no lattice solution")
            continue
        cells = " / ".join(f"{m * cost:g}" for m in found if m)
        rtp = sum(c * m for c, m in zip(coeff, found))
        print(f"  {label:28s} rtp={rtp:.6f}  [{cells}]")


if __name__ == "__main__":
    main()
