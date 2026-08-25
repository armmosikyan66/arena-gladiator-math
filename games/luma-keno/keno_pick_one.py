"""pick_1 miss/hit on the 0.950 lattice. One multiplier per hit count.

pick_1 is two outcomes (miss 30/40, hit 10/40) on the 0.1x grid, so RTP
is in steps of 0.025: 0.950 or 0.975. 0.975 busts verify_mode_volatility
(0.967). A miss remainder (0.6x vs 0.7x) lifts LUT RTP to 0.965 but
fails Base Mode STD (std falls below the 0.60 floor) and pays two
prizes for the same miss. Do not split miss weight.

Dashboard Cross-Mode RTP is 0.50pp, so picks 2-10 share this 0.950
target. low miss is 0.5x (hit 2.3x): 0.6x/2.0x has std 0.606 and sits
on the 0.60 gate.

0.65x (Keno Xtreme miss) is illegal (LUT 65).
"""

from __future__ import annotations

PICK_ONE_MISS = {
    "low": 0.5,
    "classic": 0.4,
    "medium": 0.2,
    "high": 0.1,
}

MISS_WEIGHT = 30  # C(10, 0) * C(30, 1)
HIT_WEIGHT = 10  # C(10, 1) * C(30, 0)
STD_MIN = 0.62  # dashboard Base Mode STD floor is 0.60; leave margin


def pick_one_hit(miss: float) -> float:
    return round((0.95 - 0.75 * miss) / 0.25, 1)


def pick_one_row(risk: str) -> list[float]:
    miss = PICK_ONE_MISS[risk]
    return [miss, pick_one_hit(miss)]


def pick_one_std(risk: str) -> float:
    miss, hit = pick_one_row(risk)
    mean = 0.95
    var = (
        MISS_WEIGHT * (miss - mean) ** 2 + HIT_WEIGHT * (hit - mean) ** 2
    ) / (MISS_WEIGHT + HIT_WEIGHT)
    return var**0.5


def criteria_hits(criteria: str) -> int:
    prefix, _, tail = criteria.partition("hits_")
    if prefix == "" and tail.isdigit():
        return int(tail)
    raise ValueError(f"cannot parse hits from criteria {criteria}")


assert all(pick_one_std(risk) > STD_MIN for risk in PICK_ONE_MISS)
