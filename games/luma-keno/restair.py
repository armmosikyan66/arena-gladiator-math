"""Score hand-written candidate ladders for one chart.

    python3 restair.py earn classic 10 "0.6 1.4 4 12 40 130 420 1000"

The solver finds *a* lock-clean row; it does not know that 58.4 reads worse on
a HUD than 60. This grades candidates you write by hand against the same lock
and the same RTP window, so a round column can be chosen deliberately rather
than accepted because the search happened to stop there.

Values are given in the units the chart is designed in: base-bet for Off and
Earn, cost units for the buy chips (a buy100 top of 300x base-bet is 3 here).
"""

from __future__ import annotations

import sys

import json
import os

from shape_lock import describe, lock_for, ratios_of, violations
from shape_report import HERE, RTP_WINDOW, grade, top_is_capped


def candidates(section: str, risk: str, k: int, rows: list[list[float]]) -> None:
    doc = json.load(open(os.path.join(HERE, "paytables.json"), encoding="UTF-8"))
    current = doc[section][risk][str(k)]
    row, coeff, stats, cost = grade(section, risk, k, current)
    # Same scoped lock the audit uses, so a row that grades clean here is the
    # same row shape_report will call clean.
    lock = lock_for(cost, pick=k, capped=top_is_capped(stats, cost))
    lo_w, hi_w = RTP_WINDOW

    print(f"{section}.{risk}.{k}  cost={cost:g}  window {lo_w}..{hi_w}")
    print(f"  current  {describe(coeff, row, k, lock=lock)}")
    print()

    for cand in rows:
        full = [0.0] * (k + 1)
        for h, m in zip(paying_hits_for(len(cand), k), cand):
            full[h] = m
        rtp = sum(c * m for c, m in zip(coeff, full))
        errs = violations(full, k, lock=lock)
        cells = " / ".join(f"{m * cost:g}" for m in full if m)
        rats = " ".join(f"{a}->{b}:{r:.2f}" for a, b, r in ratios_of(full))
        flag = "IN " if lo_w <= rtp <= hi_w else "OUT"
        print(f"  [{cells}]")
        print(f"    rtp={rtp:.6f} {flag}  ratios {rats}")
        print(f"    {'lock CLEAN' if not errs else 'LOCK: ' + '; '.join(errs)}")
        print()


def paying_hits_for(n_cells: int, k: int) -> list[int]:
    """Paying hits are the top `n_cells` catches: a 7-cell pick 10 pays 4..10."""
    return list(range(k - n_cells + 1, k + 1))


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    sec, rsk, kk = sys.argv[1], sys.argv[2], int(sys.argv[3])
    cands = [[float(x) for x in arg.split()] for arg in sys.argv[4:]]
    candidates(sec, rsk, kk, cands)
