#!/usr/bin/env python3
"""Per-mode dead-Lumen rate and Lumen RTP share, for the Earn tables.

Two numbers this exists to expose, neither of which the solver's own gate output
shows:

- **dead rate** — P(the row the Lumen landed on pays 0). The Lumen marks a number
  whether or not the row pays, so on high picks it usually multiplies zero. This
  is the "accidental near miss": full celebration, no money.
- **Lumen RTP share** — how much of the return arrives through the multiplier
  rather than the base table. A high share means the base table is starved and
  the session is a flat line punctuated by rare spikes.

Read against a committed baseline; `--json` emits a machine-diffable snapshot.
"""

from __future__ import annotations

import argparse
import json
from math import comb

import keno_pick_one as kp
import solve_paytables as sp

POOL = 40
DRAWN = 10


def hyper(k: int) -> list[float]:
    """P(exactly h of k picks land among the 10 drawn)."""
    return [
        comb(k, h) * comb(POOL - k, DRAWN - h) / comb(POOL, DRAWN)
        for h in range(k + 1)
    ]


def paying_set(risk: str, k: int) -> set[int]:
    if k == 1:
        return {0, 1}
    start = sp.PAY_START[risk][k]
    rh = sp.refund_hit(risk, k, True)
    return set(range(start, k + 1)) | ({rh} if rh is not None else set())


def dead_rate(risk: str, k: int) -> float:
    P = hyper(k)
    paying = paying_set(risk, k)
    return sum(P[h] for h in range(k + 1) if h not in paying)


def lumen_share(risk: str, k: int, table: list[float]) -> float:
    """Fraction of settled RTP delivered by the Lumen multiplier.

    Measured by re-settling the same table with the boost neutralised, so it
    isolates the multiplier's contribution rather than re-deriving the table.
    """
    full = kp.settled_stats(risk, k, table)["rtp"]
    saved = kp.LUMEN_BOOST[risk]
    kp.LUMEN_BOOST[risk] = 1.0
    try:
        # settled_stats itself is uncached, but it reads LUMEN_BOOST through
        # effective_coeff, which is memoised on (risk, k, paying) and so would
        # hand back the boosted coefficients after the override.
        kp.effective_coeff.cache_clear()
        flat = kp.settled_stats(risk, k, table)["rtp"]
    finally:
        kp.LUMEN_BOOST[risk] = saved
        kp.effective_coeff.cache_clear()
    return (full - flat) / full if full else 0.0


def report(tables: dict) -> list[dict]:
    rows = []
    for risk in ("classic", "low", "medium", "high"):
        for k in range(1, 11):
            table = tables[risk][str(k)]
            stats = kp.settled_stats(risk, k, table)
            rows.append(
                {
                    "mode": f"{risk}_pick_{k}_earn",
                    "risk": risk,
                    "picks": k,
                    "pay_start": sp.PAY_START[risk][k] if k >= 2 else 0,
                    "rtp": round(stats["rtp"], 4),
                    "hit_rate": round(stats["hit_rate"], 4),
                    "top": round(max(table), 1),
                    "settled_top": round(stats["max_m"], 1),
                    "dead_lumen": round(dead_rate(risk, k), 4),
                    "lumen_share": round(lumen_share(risk, k, table), 4),
                }
            )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", metavar="PATH", help="write snapshot here")
    args = ap.parse_args()

    with open("paytables.json", encoding="UTF-8") as handle:
        tables = json.load(handle)["earn"]
    rows = report(tables)

    print(
        f"{'mode':22s} {'start':>5s} {'rtp':>7s} {'hit':>7s} "
        f"{'top':>8s} {'dead%':>7s} {'lumenRTP%':>9s}"
    )
    for r in rows:
        print(
            f"{r['mode']:22s} {r['pay_start']:5d} {r['rtp']:7.4f} "
            f"{r['hit_rate']:7.4f} {r['top']:8.1f} "
            f"{r['dead_lumen'] * 100:6.1f}% {r['lumen_share'] * 100:8.1f}%"
        )

    dead = [r for r in rows if r["dead_lumen"] > 0.90 and r["picks"] >= 2]
    hoard = [r for r in rows if r["lumen_share"] > 0.50]
    print()
    print(f"modes with dead-Lumen > 90%: {len(dead)}")
    for r in sorted(dead, key=lambda r: -r["dead_lumen"]):
        print(f"  {r['mode']:22s} {r['dead_lumen'] * 100:.1f}%")
    print(f"modes with Lumen RTP share > 50%: {len(hoard)}")
    for r in sorted(hoard, key=lambda r: -r["lumen_share"]):
        print(f"  {r['mode']:22s} {r['lumen_share'] * 100:.1f}%")

    if args.json:
        with open(args.json, "w", encoding="UTF-8") as handle:
            json.dump(rows, handle, indent=2)
            handle.write("\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
