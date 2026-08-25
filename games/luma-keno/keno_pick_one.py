"""pick_1 advertised miss/hit on the 0.950 lattice.

pick_1 is two outcomes (miss 30/40, hit 10/40) on the 0.1x grid, so a
single miss/hit pair has RTP in steps of 0.025: 0.950 or 0.975. 0.975
busts verify_mode_volatility (0.967). One hit count pays one multiplier
(no remainder split). Hit is (0.95 - 0.75*miss) / 0.25.

0.65x (Keno Xtreme miss) is illegal (LUT 65); 0.6x is the legal stand-in.
"""

from __future__ import annotations

PICK_ONE_MISS = {
    "low": 0.6,
    "classic": 0.4,
    "medium": 0.2,
    "high": 0.1,
}


def pick_one_hit(miss: float) -> float:
    return round((0.95 - 0.75 * miss) / 0.25, 1)


def pick_one_row(risk: str) -> list[float]:
    miss = PICK_ONE_MISS[risk]
    return [miss, pick_one_hit(miss)]
