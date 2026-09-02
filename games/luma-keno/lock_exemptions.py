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
    ("earn", "low", 8): Exemption(
        rules=("ratio_min_mid", "last_catch"),
        reason=(
            "Easy leftover-share at advertised 100x (How-to 400x). A lock-clean "
            "6-cell ladder cannot reach the 0.963 window under that top "
            "(reachable ceiling ~0.46). Raising to ~400x would leave Easy and "
            "read as classic. Hits 3-4 carry the coefficient mass, so the body "
            "pays near 1-2x and cannot stair 2.5x into a 100x peak."
        ),
        retire_by="raise the advertised top to ~400x (leaves Easy), or drop paying tiers",
        owner="ops",
    ),
    ("earn", "low", 9): Exemption(
        rules=("ratio_min_mid", "last_catch"),
        reason=(
            "Same Easy 100x pin as pick 8. Lock-clean 7-cell RTP ceiling ~0.45. "
            "Leftover-share of the HUD is the designed body; a restair would "
            "need a ~500x advertised top."
        ),
        retire_by="raise the advertised top to ~500x (leaves Easy), or drop paying tiers",
        owner="ops",
    ),
    ("earn", "low", 10): Exemption(
        rules=("ratio_min_mid", "last_catch"),
        reason=(
            "100x is far too low for an 8-cell lock-clean ladder — reachable "
            "ceiling rtp ~0.45, and even 300x only reaches 0.61. Hits 3-4 carry "
            "~57% of the Earn coefficient mass, so a 0.965 row must pay them "
            "near 1x, which the 2.5x mid floor forbids once either cell clears "
            "the consolation line. Designed leftover-share (easy_earn_low.py) "
            "keeps the Easy ceiling so How-to settles 400x."
        ),
        retire_by="raise the advertised top to ~800-1000x, or carry fewer tiers",
        owner="ops",
    ),
    ("earn", "medium", 10): Exemption(
        rules=("ratio_min_mid", "last_catch"),
        reason=(
            "Advertised 4000x so 8/8 2000 < 9/9 3000 < 10/10 4000 on the HUD. "
            "Hit 9 is cap-pinned at 225, so 8-of-10 stays ~150 (mid 1.5x) and "
            "the last step is 17.8x (over the 15x last-catch ceiling). 1250x "
            "How-to-floor inverted the pick-8/9/10 max ladder."
        ),
        retire_by="restair with solve_row, or drop the 8-of-10 tier",
        owner="math",
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
        ("earn", "classic", 5),
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
