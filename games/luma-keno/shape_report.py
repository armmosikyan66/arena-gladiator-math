"""Audit every shipped chart against the shape lock and report feasibility.

Read-only. Prints, per row: the printed cells, settled RTP, adjacent ratios,
the hit that carries the return, lock violations, and - when the top is frozen
- whether any lock-clean ladder can reach the designed RTP window at all.

Denomination matters. Off rows are base-bet multiples graded on plain
hypergeometric coefficients. Earn rows are advertised multiples that settle
through Lumen and Pulse. Buy rows are stored in paytables.json as base-bet
multiples but are *designed and graded in cost units*, so they are divided by
the chip cost before the lock reads them - a buy cell of 1x means "returns the
buy price", which is the line that decides consolation.
"""

from __future__ import annotations

import json
import os
import sys

from keno_pick_one import lumen_placed_on_pick
from lock_exemptions import coverage, exemption_for
from shape_lock import (
    LADDER_MIN_PICK,
    describe,
    feasible_rtp_range,
    lock_for,
    min_top_for,
    paying_hits,
    violations,
)
from solve_paytables import (
    BUY_COSTS,
    MAX_PAYOUT_ABS,
    mode_stats_for,
    pay_coeff,
)

HERE = os.path.dirname(os.path.abspath(__file__))
RTP_WINDOW = (0.9630, 0.9655)
RISKS = ("low", "classic", "medium", "high")
SECTIONS = ("risks", "earn", "buy10", "buy100")


def grade(section: str, risk: str, k: int, json_row: list[float]):
    """(row in design units, coefficient vector, settled RTP, cost)."""
    cost = BUY_COSTS.get(section, 1.0)
    row = [round(m / cost, 6) for m in json_row] if cost != 1.0 else list(json_row)
    earn = section != "risks"
    bought = section in BUY_COSTS
    placed = lumen_placed_on_pick(section, k) if bought else False
    buy = section if bought else None
    coeff = pay_coeff(risk, k, earn, bought, placed, buy, cost)
    stats = mode_stats_for(risk, k, row, earn, bought, placed, cost, buy)
    return row, coeff, stats, cost


def top_is_capped(stats: dict, cost: float) -> bool:
    """True when the settled top sits on the absolute payout ceiling.

    A ceiling-bound jackpot cannot be raised to satisfy the 8x final-catch
    floor, so enforcing that floor would only push the tier beneath it under
    the stake. `shape_lock.scoped` grades those rows with the final catch as an
    ordinary step instead.
    """
    return abs(stats["max_m"] * cost - MAX_PAYOUT_ABS[cost]) < 1e-6


def audit(only: str | None = None, verbose: bool = True) -> list[str]:
    doc = json.load(open(os.path.join(HERE, "paytables.json"), encoding="UTF-8"))
    dirty: list[str] = []
    graded: dict[tuple[str, str, int], bool] = {}
    for section in SECTIONS:
        if section not in doc:
            continue
        for risk in RISKS:
            if risk not in doc.get(section, {}):
                continue
            for k_s, json_row in sorted(
                doc[section][risk].items(), key=lambda t: int(t[0])
            ):
                k = int(k_s)
                if k < 2:
                    continue  # pick_1 is a closed-form lattice, not a ladder
                name = f"{section}.{risk}.{k}"
                if only and only not in name:
                    continue
                row, coeff, stats, cost = grade(section, risk, k, json_row)
                capped = top_is_capped(stats, cost)
                lock = lock_for(cost, pick=k, capped=capped)
                errs = violations(row, k, lock=lock)
                graded[(section, risk, k)] = not errs
                scope = []
                if k < LADDER_MIN_PICK:
                    scope.append("short-pick scope")
                if capped:
                    scope.append("ceiling-bound top")
                note = f"  [{', '.join(scope)}]" if scope else ""
                if not errs:
                    if verbose:
                        print(
                            f"{name:22s} clean   {describe(coeff, row, k, lock=lock)}"
                            f"{note}"
                        )
                    continue

                dirty.append(name)
                hits = paying_hits(row)
                top = max(row)
                waiver = exemption_for(section, risk, k)
                print(f"\n{name:22s} {len(errs)} violation(s)  cost={cost:g}{note}")
                if waiver:
                    print(
                        f"  EXEMPT ({', '.join(waiver.rules)}) owner={waiver.owner}\n"
                        f"    {waiver.reason}\n"
                        f"    retire by: {waiver.retire_by}"
                    )
                print(f"  {describe(coeff, row, k, lock=lock)}")
                print(f"  settled rtp={stats['rtp']:.6f} max_m={stats['max_m']:.1f}")
                lo, hi = feasible_rtp_range(coeff, hits, top, lock=lock)
                fits = lo <= RTP_WINDOW[1] + 1e-12 and hi >= RTP_WINDOW[0] - 1e-12
                print(
                    f"  lock-clean RTP reachable with top {top:g} and "
                    f"{len(hits)} paying cells: {lo:.4f}..{hi:.4f}  "
                    f"window {RTP_WINDOW[0]}..{RTP_WINDOW[1]}  "
                    f"{'REACHABLE' if fits else '>>> UNREACHABLE <<<'}"
                )
                if not fits:
                    need = min_top_for(hits, floor=row[hits[0]], lock=lock)
                    print(
                        f"  min top that can stair {len(hits)} cells from "
                        f"{row[hits[0]]:g}: {need:.4g}  (frozen top {top:g})"
                    )
                for e in errs:
                    print(f"    - {e}")
    _report_coverage(graded)
    return [n for n in dirty if exemption_for(*_key(n)) is None]


def _key(name: str) -> tuple[str, str, int]:
    section, risk, k = name.split(".")
    return section, risk, int(k)


def _report_coverage(graded: dict[tuple[str, str, int], bool]) -> None:
    if not graded:
        return
    c = coverage(graded)
    print(
        f"\nlock coverage: {c['clean']}/{c['rows']} rows clean ({c['locked_pct']}%), "
        f"{c['exempt']} exempt, {c['grandfathered']} pre-lock, "
        f"{c['unexplained']} unexplained"
    )


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quiet = "-q" in sys.argv
    bad = audit(args[0] if args else None, verbose=not quiet)
    # Exempt rows are known debt and do not count here; an unexplained failure
    # is the thing that should stop a build.
    print(f"\n{len(bad)} row(s) violate the shape lock without an exemption")
    if bad:
        print("  " + ", ".join(bad))
