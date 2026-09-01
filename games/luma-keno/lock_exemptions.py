"""Rows that ship without satisfying the shape lock, and why.

A lock whose only outcomes are "clean" or "blocked" gets switched off the first
time it collides with a shipped jackpot. This registry is the third outcome:
the row ships, the violation is named, and someone owns it. Nothing here is a
silent pass - `shape_report` prints every exemption on every run, and
`coverage()` reports how much of the fleet is genuinely locked so the number
can be ratcheted upward the way `evals/baseline.json` is.

An exemption is not a place to park a row you have not looked at. Each one
records the rule it breaks, why the row cannot satisfy it, and what would have
to change to retire it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Exemption:
    rules: tuple[str, ...]
    reason: str
    #: What would have to change for this row to become lock-clean.
    retire_by: str
    owner: str


#: (section, risk, pick) -> why this row ships non-compliant.
EXEMPTIONS: dict[tuple[str, str, int], Exemption] = {
    ("risks", "high", 10): Exemption(
        rules=("ratio_max",),
        reason=(
            "4.3 -> 78.5 is an 18.26x body step, above the 8x mid ceiling. The "
            "row is the certified restair (rtp 0.964383) and must not regress; "
            "the step reads as the volatility wall but sits one pair above the "
            "consolation crossing, so the wall allowance does not formally "
            "cover it."
        ),
        retire_by="re-solve with the wall placed on 0.4 -> 4.3, if Ops will move 78.5",
        owner="ops",
    ),
    ("risks", "classic", 10): Exemption(
        rules=("ratio_min_mid",),
        reason=(
            "1000x cannot host a lock-clean 8-cell ladder: the tightest legal "
            "chain tops out at rtp 0.679, below the 0.9630 window. The restair "
            "from 1.9 / 2.0 / 2.1 to 1.6 / 2.3 / 3.1 removed the flat pack, "
            "which was the actual defect."
        ),
        retire_by="raise the top to ~1418x, or drop a paying tier",
        owner="ops",
    ),
    ("risks", "high", 8): Exemption(
        rules=("ratio_min_mid", "ratio_max", "no_mega_jump"),
        reason=(
            "39.6 / 40 is a genuine HUD-flat pair and should be fixed, but no "
            "lock-clean ladder exists at 25000x: the floor is rtp 0.9704, above "
            "the window. Cutting the top to 22000x fixes it with hit rate "
            "intact; keeping 25000x costs the hit-3 tier and takes hit rate "
            "from 31.2% to 8.9%."
        ),
        retire_by="cut the top to 22000x (recommended) or drop the hit-3 tier",
        owner="ops",
    ),
    ("earn", "low", 10): Exemption(
        rules=("ratio_min_mid",),
        reason=(
            "100x is far too low for an 8-cell ladder - the reachable ceiling "
            "is rtp 0.4465, and even 300x only reaches 0.6086. Hits 3-4 carry "
            "~57% of the coefficient mass, so a 0.963 row must pay them near "
            "1x, which the 2.5x mid floor forbids once either cell clears the "
            "consolation line."
        ),
        retire_by="raise the advertised top to ~800-1000x, or carry fewer tiers",
        owner="ops",
    ),
}


#: Certified before the lock existed and not yet restaired. These are the fleet
#: inventory, not decisions: each one is a row whose column has never been read
#: against the ladder rules. They ship because they are already certified and
#: the lock is not retroactive, and they are listed one by one so the set can
#: only shrink - dropping a row from this list is how coverage ratchets.
#:
#: This is deliberately not a wildcard. A new row that fails is unexplained and
#: should stop a build; only rows that predate the lock get the grandfather.
GRANDFATHERED: frozenset[tuple[str, str, int]] = frozenset(
    {
        ("risks", "low", 8), ("risks", "low", 9), ("risks", "low", 10),
        ("risks", "classic", 7), ("risks", "classic", 8), ("risks", "classic", 9),
        ("risks", "medium", 8), ("risks", "medium", 9),
        ("earn", "low", 4), ("earn", "low", 7), ("earn", "low", 8),
        ("earn", "low", 9),
        ("earn", "classic", 5), ("earn", "classic", 6), ("earn", "classic", 9),
        ("earn", "medium", 5), ("earn", "medium", 8), ("earn", "medium", 9),
        ("earn", "medium", 10),
        ("earn", "high", 8), ("earn", "high", 9), ("earn", "high", 10),
        ("buy10", "low", 6), ("buy10", "low", 9), ("buy10", "low", 10),
        ("buy10", "classic", 9), ("buy10", "classic", 10),
        ("buy10", "medium", 6), ("buy10", "medium", 8),
        ("buy10", "high", 8), ("buy10", "high", 9), ("buy10", "high", 10),
        ("buy100", "low", 6), ("buy100", "low", 9), ("buy100", "low", 10),
        ("buy100", "high", 10),
        # Short-pick cliffs - the priority-6 work item. A shallow card has few
        # cells, so the body carries the whole return and a single step ends up
        # doing all the work: risks.high.7 jumps 21x at 4->5, buy100.classic.5
        # 8.5x at 3->4. Off high 6 was the first of these and is now restaired
        # (3 / 10 / 79 / 3484.6); the rest follow the same method.
        ("risks", "classic", 6), ("risks", "high", 5), ("risks", "high", 7),
        ("earn", "high", 7),
        ("buy10", "classic", 3), ("buy10", "classic", 5),
        ("buy10", "medium", 5), ("buy10", "high", 5),
        ("buy100", "classic", 3), ("buy100", "classic", 5),
        ("buy100", "medium", 5), ("buy100", "high", 5), ("buy100", "high", 7),
    }
)

_GRANDFATHER = Exemption(
    rules=("*",),
    reason=(
        "certified before the shape lock existed; the column has not been read "
        "against the ladder rules yet"
    ),
    retire_by="restair the row, or record a specific exemption for it",
    owner="math",
)


def exemption_for(section: str, risk: str, k: int) -> Exemption | None:
    key = (section, risk, k)
    if key in EXEMPTIONS:
        return EXEMPTIONS[key]
    return _GRANDFATHER if key in GRANDFATHERED else None


def coverage(
    graded: dict[tuple[str, str, int], bool],
) -> dict[str, float | int]:
    """Lock coverage over the rows `shape_report` graded.

    `graded` maps each row to whether it is clean. Exempt rows count as neither
    clean nor failing: they are known debt. A failing row that is *not* exempt
    is the thing that should break a build.
    """
    total = len(graded)
    clean = sum(1 for ok in graded.values() if ok)
    named = sum(1 for key, ok in graded.items() if not ok and key in EXEMPTIONS)
    grandfathered = sum(
        1
        for key, ok in graded.items()
        if not ok and key not in EXEMPTIONS and key in GRANDFATHERED
    )
    unexplained = total - clean - named - grandfathered
    return {
        "rows": total,
        "clean": clean,
        "exempt": named,
        "grandfathered": grandfathered,
        "unexplained": unexplained,
        "locked_pct": round(100.0 * clean / total, 1) if total else 0.0,
    }
