"""pick_1 miss/hit plus Lumen/extra spin criteria.

pick_1 is two advertised outcomes (miss 30/40, hit 10/40) on the 0.1x grid.
Catching Lumen multiplies a paying hit, so the lattice is
`0.75*miss + c_hit*hit = 0.950` with `c_hit > 0.25`. 0.975 still busts
`verify_mode_volatility` (0.967). Do not split miss weight.

Dashboard Cross-Mode RTP is 0.50pp, so picks 2-10 share this 0.950
target after extras and Lumen are priced in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from math import comb

STD_MIN = 0.62  # dashboard Base Mode STD floor is 0.60; leave margin

POOL = 40
DRAWN = 10
REST = 30
EXTRA_N = 2
CHANCE_DENOM = 100

# Off (table-only) pick_1 lattice. Earn pick_1 is solved with Lumen priced in.
PICK_ONE_MISS = {
    "low": 0.5,
    "classic": 0.4,
    "medium": 0.2,
    "high": 0.1,
}
MISS_WEIGHT = 30
HIT_WEIGHT = 10
EXTRA_CHANCE_PCT = {
    "classic": 16,
    "low": 10,
    "medium": 7,
    "high": 4,
}
# Earn-only: one round Pulse ×2, independent of extras. Off never rolls it.
PULSE_BOOST = 2.0
PULSE_CHANCE_PCT = 10
LUMEN_BOOST = {
    "classic": 2.0,
    "low": 2.0,
    "medium": 2.0,
    "high": 5.0,
}
EXTRA_REASONS = ("none", "lumen", "near", "luck")
REASON_TO_EVENT = {
    "none": None,
    "lumen": "lumen",
    "near": "nearMiss",
    "luck": "natural",
}

_SPIN_RE = re.compile(
    r"^hits_(\d+)_lumen_([01])_extra_([01])_(none|lumen|near|luck)_(\d+)(?:_pulse_([01]))?$"
)


@dataclass(frozen=True)
class SpinCriteria:
    main_hits: int
    lumen_hit: bool
    extras: bool
    extra_reason: str
    extra_hits: int
    pulse: bool = False

    @property
    def total_hits(self) -> int:
        return self.main_hits + self.extra_hits


def parse_mode_name(name: str) -> tuple[str, int, bool]:
    """'{risk}_pick_{k}' or '{risk}_pick_{k}_earn' → (risk, k, earn)."""
    earn = name.endswith("_earn")
    core = name[: -5] if earn else name
    risk, pick = core.rsplit("_pick_", 1)
    return risk, int(pick), earn


def mode_name(risk: str, k: int, earn: bool = False) -> str:
    base = f"{risk}_pick_{k}"
    return f"{base}_earn" if earn else base


def base_hit_weight(k: int, h: int, drawn: int = DRAWN, rest: int = REST) -> int:
    if h < 0 or h > k or (k - h) > rest or h > drawn:
        return 0
    return comb(drawn, h) * comb(rest, k - h)


def pick_one_hit(miss: float) -> float:
    return round((0.95 - 0.75 * miss) / 0.25, 1)


def pick_one_row(risk: str) -> list[float]:
    """Off-mode advertised miss/hit (no Lumen)."""
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
    return parse_spin_criteria(criteria).main_hits


def criteria_lumen_hit(criteria: str) -> bool:
    return parse_spin_criteria(criteria).lumen_hit


def parse_hits_criteria(criteria: str) -> tuple[int, bool]:
    spin = parse_spin_criteria(criteria)
    return spin.main_hits, spin.lumen_hit


def parse_spin_criteria(criteria: str) -> SpinCriteria:
    """Parse `hits_{h}_lumen_{0|1}_extra_{0|1}_{none|lumen|near|luck}_{eh}`."""
    match = _SPIN_RE.match(criteria)
    if match:
        main_hits = int(match.group(1))
        lumen_hit = match.group(2) == "1"
        extras = match.group(3) == "1"
        extra_reason = match.group(4)
        extra_hits = int(match.group(5))
        pulse = match.group(6) == "1" if match.group(6) is not None else False
        if extras == (extra_reason == "none") or (not extras and extra_hits != 0):
            raise ValueError(f"cannot parse extras from criteria {criteria}")
        return SpinCriteria(main_hits, lumen_hit, extras, extra_reason, extra_hits, pulse)

    prefix, _, rest = criteria.partition("hits_")
    if prefix != "" or rest == "":
        raise ValueError(f"cannot parse hits from criteria {criteria}")
    if "_lumen_" in rest:
        hits_s, _, flag = rest.partition("_lumen_")
        if hits_s.isdigit() and flag in ("0", "1"):
            lumen_hit = flag == "1"
            return SpinCriteria(
                int(hits_s), lumen_hit, lumen_hit, "lumen" if lumen_hit else "none", 0, False
            )
        raise ValueError(f"cannot parse hits from criteria {criteria}")
    if rest.isdigit():
        hits = int(rest)
        return SpinCriteria(hits, False, False, "none", 0)
    raise ValueError(f"cannot parse hits from criteria {criteria}")


def lumen_books_for_hits(hits: int, drawn: int = DRAWN) -> list[bool]:
    if hits <= 0:
        return [False]
    if hits >= drawn:
        return [True]
    return [False, True]


def lumen_hit_factor(hits: int, lumen_hit: bool, drawn: int = DRAWN) -> int:
    """How many of the `drawn` marked slots realize this lumenHit flag."""
    return hits if lumen_hit else drawn - hits


def extra_pair_weight(
    k: int,
    main_hits: int,
    extra_hits: int,
    extra_n: int = EXTRA_N,
    rest: int = REST,
) -> int:
    remaining_picks = k - main_hits
    remaining_miss = rest - remaining_picks
    miss_draw = extra_n - extra_hits
    if extra_hits < 0 or miss_draw < 0:
        return 0
    if extra_hits > remaining_picks or miss_draw > remaining_miss:
        return 0
    return comb(remaining_picks, extra_hits) * comb(remaining_miss, miss_draw)


def extra_hit_js(k: int, main_hits: int) -> list[int]:
    js = [j for j in range(EXTRA_N + 1) if extra_pair_weight(k, main_hits, j) > 0]
    return js or [0]


def extras_forced_reason(k: int, main_hits: int, lumen_hit: bool) -> str | None:
    if lumen_hit:
        return "lumen"
    if k >= 4 and main_hits == k - 1:
        return "near"
    return None


def extra_outcomes(k: int, main_hits: int, lumen_hit: bool) -> list[tuple[bool, str, int]]:
    """Earn extras: first match lumen → near-miss → luck (main_hits >= 2).

    Luck weight is EXTRA_CHANCE_PCT[risk] / 100 of the leftover after Lumen
    and near-miss. It is 0 at pick_1 (cannot have two main hits).
    """
    forced = extras_forced_reason(k, main_hits, lumen_hit)
    js = extra_hit_js(k, main_hits)
    if forced:
        return [(True, forced, j) for j in js]
    if main_hits >= 2:
        return [(False, "none", 0)] + [(True, "luck", j) for j in js]
    return [(False, "none", 0)]


def spin_outcomes(k: int, drawn: int = DRAWN) -> list[SpinCriteria]:
    out: list[SpinCriteria] = []
    for main_hits in range(k + 1):
        for lumen_hit in lumen_books_for_hits(main_hits, drawn):
            for extras, reason, extra_hits in extra_outcomes(k, main_hits, lumen_hit):
                for pulse in (False, True):
                    out.append(
                        SpinCriteria(main_hits, lumen_hit, extras, reason, extra_hits, pulse)
                    )
    return out


def book_count_for_picks(k: int, drawn: int = DRAWN) -> int:
    return len(spin_outcomes(k, drawn))


def hit_criteria_base(hits: int) -> str:
    return f"hits_{hits}"


def hit_criteria_name(spin: SpinCriteria) -> str:
    return (
        f"hits_{spin.main_hits}_lumen_{int(spin.lumen_hit)}"
        f"_extra_{int(spin.extras)}_{spin.extra_reason}_{spin.extra_hits}"
        f"_pulse_{int(spin.pulse)}"
    )


def spin_weight(
    k: int,
    spin: SpinCriteria,
    risk: str,
    drawn: int = DRAWN,
    rest: int = REST,
) -> int:
    base = (
        comb(drawn, spin.main_hits)
        * comb(rest, k - spin.main_hits)
        * lumen_hit_factor(spin.main_hits, spin.lumen_hit, drawn)
    )
    pair_total = comb(rest, EXTRA_N)
    pair = extra_pair_weight(k, spin.main_hits, spin.extra_hits)
    chance = EXTRA_CHANCE_PCT[risk]
    pulse_part = PULSE_CHANCE_PCT if spin.pulse else (CHANCE_DENOM - PULSE_CHANCE_PCT)
    forced = extras_forced_reason(k, spin.main_hits, spin.lumen_hit)
    if not spin.extras:
        if forced:
            raise ValueError(f"forced extras closed: {spin}")
        if spin.main_hits >= 2:
            extra_part = (CHANCE_DENOM - chance) * pair_total
        else:
            extra_part = CHANCE_DENOM * pair_total
        return base * extra_part * pulse_part
    if spin.extra_reason in ("lumen", "near"):
        return base * CHANCE_DENOM * pair * pulse_part
    if spin.extra_reason == "luck":
        return base * chance * pair * pulse_part
    raise ValueError(f"open extras with reason {spin.extra_reason}")


def weight_scale() -> int:
    return CHANCE_DENOM * comb(REST, EXTRA_N) * CHANCE_DENOM


def lumen_pay(base: float, lumen_hit: bool, risk: str) -> float:
    """Table × Lumen. Catching does not rescue a 0× row."""
    if lumen_hit and base > 0:
        return round(float(base) * LUMEN_BOOST[risk], 1)
    return round(float(base), 1)


def pulse_pay(amount: float, pulse: bool) -> float:
    """Paying table × Pulse. Pulse does not rescue a 0× row."""
    if pulse and amount > 0:
        return round(float(amount) * PULSE_BOOST, 1)
    return round(float(amount), 1)


def settle_pay(base: float, lumen_hit: bool, pulse: bool, risk: str) -> float:
    """Table × Lumen × Pulse. Neither bonus rescues a 0× row."""
    return pulse_pay(lumen_pay(base, lumen_hit, risk), pulse)


def lumen_boost_applied(base: float, lumen_hit: bool, risk: str) -> float:
    if lumen_hit and base > 0:
        return LUMEN_BOOST[risk]
    return 1.0


def pulse_boost_applied(amount: float, pulse: bool) -> float:
    if pulse and amount > 0:
        return PULSE_BOOST
    return 1.0


def weight_total(k: int, drawn: int = DRAWN) -> int:
    return comb(POOL, k) * drawn * weight_scale()


@lru_cache(maxsize=None)
def effective_coeff(risk: str, k: int, paying: frozenset[int]) -> tuple[float, ...]:
    """RTP = sum_h coeff[h] * advertised[h] when advertised[h] > 0 iff h in paying.

    Lumen and Pulse are priced in: a paying row that is caught contributes
    boost * P; Pulse ×2 on 10% of Earn books.
    """
    total = weight_total(k)
    boost = LUMEN_BOOST[risk]
    coeff = [0.0] * (k + 1)
    for spin in spin_outcomes(k):
        hits = spin.total_hits
        if hits not in paying:
            continue
        factor = boost if spin.lumen_hit else 1.0
        if spin.pulse:
            factor *= PULSE_BOOST
        coeff[hits] += spin_weight(k, spin, risk) * factor / total
    return tuple(coeff)


def settled_pairs(risk: str, k: int, table: list[float]) -> list[tuple[int, float]]:
    """(weight, settled multiplier) for every spin book."""
    return [
        (
            spin_weight(k, spin, risk),
            settle_pay(table[spin.total_hits], spin.lumen_hit, spin.pulse, risk),
        )
        for spin in spin_outcomes(k)
    ]


def settled_rtp(risk: str, k: int, table: list[float]) -> float:
    total = weight_total(k)
    return sum(w * m for w, m in settled_pairs(risk, k, table)) / total


def settled_stats(risk: str, k: int, table: list[float]) -> dict:
    total = weight_total(k)
    pairs = settled_pairs(risk, k, table)
    rtp = sum(w * m for w, m in pairs) / total
    var = sum(w * (m - rtp) ** 2 for w, m in pairs) / total
    p5k = sum(w for w, m in pairs if m >= 5000) / total
    p10k = sum(w for w, m in pairs if m >= 10000) / total
    etl40 = sum(w * m for w, m in pairs if m >= 40) / total
    etl10k = sum(w * m for w, m in pairs if m >= 10000) / total
    ranked = sorted(pairs, key=lambda t: t[1])
    cum = 0.0
    tail_start = ranked[0][1] if ranked else 0.0
    for w, m in ranked:
        cum += w / total
        if cum >= 0.999:
            tail_start = m
            break
    tail_p = sum(w for w, m in pairs if m >= tail_start) / total
    cvar = (sum(w * m for w, m in pairs if m >= tail_start) / total / tail_p) if tail_p else 0.0
    return {
        "rtp": rtp,
        "std": var**0.5,
        "p5k": p5k,
        "p10k": p10k,
        "etl40": etl40,
        "etl10k": etl10k,
        "cvar": cvar,
        "max_m": max(m for _, m in pairs),
        "hit_rate": sum(w for w, m in pairs if m > 0) / total,
        "nonzero_payouts": sorted({m for _, m in pairs if m > 0}),
    }


@lru_cache(maxsize=None)
def pick_one_row_earn(risk: str) -> list[float]:
    """Earn advertised miss/hit so settled RTP (with Lumen) is ~0.950."""
    coeff = effective_coeff(risk, 1, frozenset({0, 1}))
    best: tuple[float, float, list[float]] | None = None
    for miss_i in range(1, 16):
        miss = miss_i / 10
        for hit_i in range(miss_i + 1, 81):
            hit = hit_i / 10
            rtp = coeff[0] * miss + coeff[1] * hit
            err = abs(rtp - 0.95)
            if err > 0.0025:
                continue
            table = [miss, hit]
            stats = settled_stats(risk, 1, table)
            if stats["std"] < STD_MIN:
                continue
            key = (err, -miss)
            if best is None or key < (best[0], -best[2][0]):
                best = (err, stats["std"], table)
    if best is None:
        raise ValueError(f"no pick_1 lattice for {risk} with Lumen priced in")
    return best[2]


def pick_one_std_earn(risk: str) -> float:
    return settled_stats(risk, 1, pick_one_row_earn(risk))["std"]


assert all(pick_one_std(risk) > STD_MIN for risk in PICK_ONE_MISS)
assert all(pick_one_std_earn(risk) > STD_MIN for risk in LUMEN_BOOST)
assert abs(settled_rtp("classic", 1, pick_one_row_earn("classic")) - 0.95) <= 0.0025
assert book_count_for_picks(1) == 6
assert lumen_hit_factor(0, False) == 10
assert lumen_hit_factor(3, True) == 3
assert extra_pair_weight(5, 5, 0) == comb(REST, EXTRA_N)
assert extra_pair_weight(5, 4, 2) == 0
assert parse_spin_criteria("hits_3_lumen_1_extra_1_lumen_1_pulse_1") == SpinCriteria(
    3, True, True, "lumen", 1, True
)
assert lumen_pay(2.6, True, "classic") == 5.2
assert settle_pay(2.6, True, True, "classic") == 10.4
assert lumen_pay(0.0, True, "high") == 0.0
assert pulse_pay(0.0, True) == 0.0
assert lumen_pay(2.6, False, "classic") == 2.6
assert lumen_boost_applied(0.0, True, "high") == 1.0
assert lumen_boost_applied(2.6, True, "medium") == 2.0
assert pulse_boost_applied(5.2, True) == 2.0
assert sum(spin_weight(1, spin, "classic") for spin in spin_outcomes(1)) == comb(40, 1) * DRAWN * weight_scale()
assert sum(spin_weight(5, spin, "classic") for spin in spin_outcomes(5)) == comb(40, 5) * DRAWN * weight_scale()
