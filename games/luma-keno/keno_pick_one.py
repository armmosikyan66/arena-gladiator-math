"""pick_1 miss/hit plus Lumen/extra spin criteria.

pick_1 is two advertised outcomes (miss 30/40, hit 10/40).
Catching Lumen multiplies a paying hit, so the lattice is
`0.75*miss + c_hit*hit = RTP_TARGET` with `c_hit > 0.25`. 0.975 busts
`verify_mode_volatility` (0.967).

Dashboard Cross-Mode RTP is 0.50pp and includes pick_1, so every Off
pick_1 risk keeps the miss-bonus third tier (6 of 30 misses pay +0.1).

**Off pick_1 advertises two outcomes — one miss, one hit.** With two
tiers the reachable RTPs are `0.75*m + 0.25*h`; both legs are multiples of
0.1 (RGS `payout % 10 == 0`), so the lattice is `0.025*(3j + i)`. 0.950 is
on it; 0.965 is not; the next point up is 0.975, over the 0.967 ceiling.

Dashboard Cross-Mode is 0.50pp and includes every published mode — a
local exemption for 0.950 pick_1 reads as 1.50–1.62pp against the 0.965
fleet and fails certification. The 1.5pp gap is closed by a third miss
tier: 6 of 30 miss books pay `miss + 0.1` (1 in 5 misses). Advertised
row stays the two-cell pair; LUT RTP becomes 0.9650. Picks 2–10 are
untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from math import comb

STD_MIN = 0.62  # dashboard Base Mode STD floor is 0.60; leave margin

# Single source of truth for the advertised return. Imported by
# solve_paytables.py — do not re-declare it there.
#
# 0.9650 (was 0.9500). House edge 5.0% -> 3.5%, a 30% cut in bleed rate and the
# largest single lever on session length in the system.
RTP_TARGET = 0.9650
# Dashboard 3-star per-mode volatility ceiling. Never solve above this.
RTP_CEILING = 0.967
# Per-mode acceptance band. Asymmetric because both edges are pinned by
# something real, not by symmetry around the target:
#
#   upper 0.9665 — the naive 0.965 + 0.0025 is 0.9675, over RTP_CEILING.
#   lower 0.9628 — pick_1 Earn pays are multiples of 0.1x (lumen_pay rounds to
#     1dp), which makes reachable RTP a coarse lattice. medium_pick_1_earn can
#     reach exactly one point in this band, 0.9630, so the floor has to sit just
#     below it. The 0.0002 of clearance is for float representation only; the
#     next lattice point down is 0.9600, 30x further away.
#
# Width is 0.37pp, inside the 0.50pp Cross-Mode Consistency gate. Raising the
# floor past 0.9630 makes medium_pick_1_earn unsolvable.
#
# This floor is only this tight because LUMEN_BOOST["high"] came down to 2.0. At
# 5.0, gcd(825, 385) = 55 spaced high_pick_1_earn's options 0.0055 apart and
# 0.9625 was its only legal value, forcing a 0.9620 floor.
#
# Lives here rather than in solve_paytables.py because pick_one_row_earn has to
# search against it. When the band was only known to the caller, that search
# used a hardcoded +/-0.0025 and returned a point outside the band.
MODE_RTP_BAND = (0.9628, 0.9665)
assert MODE_RTP_BAND[0] < RTP_TARGET < MODE_RTP_BAND[1] < RTP_CEILING
assert MODE_RTP_BAND[1] - MODE_RTP_BAND[0] < 0.005, "busts Cross-Mode gate"

# What an advertised Off pick_1 miss/hit pair can reach on its own: multiples of
# 0.025, so the best point at or below target is 0.950. The gap to RTP_TARGET is
# closed by the third tier, not by moving this.
PICK_ONE_BASE_RTP = 0.950

POOL = 40
DRAWN = 10
REST = 30
EXTRA_N = 2
CHANCE_DENOM = 100

# Off (table-only) pick_1 lattice. Earn pick_1 is solved with Lumen priced in.
#
# pick_1 is the one mode where the LDW band is unreachable. Two outcomes and
# P(hit) = 0.25 make it a line, not a surface: 0.75*miss + 0.25*hit = RTP. Any
# miss in (0, 1) pays something on the losing outcome, so LDW is 75%; miss = 0
# makes it 0%. Nothing in between exists, and a push (miss = 1.0) is impossible
# because it would spend 0.75 of a 0.965 budget and leave the *hit* tier paying
# 0.86x — below the stake, and below the miss.
#
# The fork is resolved to "keep the gentle bleed", and not as a preference — the
# jackpot branch is blocked by certification. With miss = 0 an Off pick_1 row has
# exactly one distinct nonzero payout, and check_gates requires two. Earn escapes
# that only because Lumen x5 manufactures a second tier (2.5 and 12.5 on high),
# so taking the branch would leave Off and Earn with opposite LDW shapes on the
# same mode. Two further reasons not to reach for it:
#
#   - Flipping all four risks to miss = 0 makes every row identical
#     ([0.0, 3.86]) and quietly turns the risk selector into a no-op on 1 pick.
#   - The gate's own comment scopes it to "k >= 2", so k = 1 arguably slips
#     through by accident. Rewriting a certification gate to admit a shape we
#     happen to want is the wrong direction of causation; if pick_1 should be
#     allowed a single paying tier, that is a dashboard question, not a solver
#     edit.
#
# Consequence to carry forward: pick_1 stays at 75% LDW and is the one mode
# structurally outside the 15-22% band. It is 8 of 80 modes and the shallowest
# ladder, so it does not dominate the session-level rate.
PICK_ONE_MISS = {
    "low": 0.5,
    "classic": 0.4,
    "medium": 0.2,
    "high": 0.1,
}
MISS_WEIGHT = 30
HIT_WEIGHT = 10
# Off pick_1's third tier. `MISS_WEIGHT` books split into `MISS_WEIGHT -
# PICK_ONE_BONUS_WEIGHT` at `miss` and `PICK_ONE_BONUS_WEIGHT` at `miss +
# PICK_ONE_BONUS`. The base pair sits on the 0.950 lattice and the split adds
# the remaining 1.5pp; see the module docstring for why a two-tier pick_1
# cannot reach 0.9650 at all.
#
# Every Off pick_1 risk keeps the +0.1 miss-bonus tier. Dashboard
# Cross-Mode includes pick_1; a 0.950 two-outcome card fails it by 1.5pp.
PICK_ONE_BONUS = 0.1
#: Risks whose Off pick_1 keeps the miss-bonus third tier.
PICK_ONE_BONUS_RISKS = frozenset(PICK_ONE_MISS)
PICK_ONE_BONUS_WEIGHT = round(
    (RTP_TARGET - PICK_ONE_BASE_RTP) * (MISS_WEIGHT + HIT_WEIGHT) / PICK_ONE_BONUS
)
assert PICK_ONE_BONUS_WEIGHT == 6, "expected 6 upgraded miss books"
assert 0 < PICK_ONE_BONUS_WEIGHT < MISS_WEIGHT
EXTRA_CHANCE_PCT = {
    "classic": 16,
    "low": 10,
    "medium": 7,
    "high": 4,
}
# Earn-only: Pulse rides the extra lights. Boost is ×2 on every risk.
# Chance is 10% of extra-open rounds on picks 2–10 (and every buy round
# with 2+ picks). Pick_1 is the exception: a shared 10% collapses all four
# Earn pick_1 rows onto 0.5/2.1, so pick_1 uses a per-risk chance that puts
# Off's miss ladder on the 0.1× grid inside MODE_RTP_BAND.
PULSE_BOOST = {
    "classic": 2.0,
    "low": 2.0,
    "medium": 2.0,
    "high": 2.0,    # not x5: Off 50000 x2 x5 How-to = 500000 over the 100k cap
}
PULSE_CHANCE_PCT = 10
PULSE_CHANCE_PICK_ONE_PCT = {
    "low": 10,       # 0.5 / 2.1
    "classic": 4,    # 0.4 / 2.4
    "medium": 12,    # 0.2 / 2.9
    "high": 6,       # 0.1 / 3.2
}


def pulse_chance_pct(risk: str, k: int) -> int:
    """Pulse roll rate among extra-open books for this risk and pick count."""
    return PULSE_CHANCE_PICK_ONE_PCT[risk] if k == 1 else PULSE_CHANCE_PCT
# high was 5.0, which put 69-74% of the return on picks 5-10 into a channel that
# pays on under 3% of rounds: the base table was left doing a quarter of its
# nominal job, so a session read as a flat line punctuated by rare spikes.
#
# 2.0 is the value, and the intermediate steps were measured rather than assumed:
#
#   L=5.0 -> 8 modes over 50% Lumen share, peak 74.0%
#   L=4.0 -> 8 modes over 50% Lumen share, peak 68.2%   (barely moves)
#   L=3.0 -> unsolvable; see below
#   L=2.0 -> 0 modes over 50%, peak 42.3%, cross-mode spread 0.0031 -> 0.0028
#
# 3.0 is not available at all: it makes gcd(825, 330) = 165, so high_pick_1_earn
# can only reach 0.9570 or 0.9735 and neither is inside MODE_RTP_BAND.
#
# What this does *not* cost is the top prize. advertised_cap divides by
# settle_factor, so lowering the boost raises the advertised row instead —
# high_pick_10_earn goes 490x advertised / 4900x settled to 1225x / 4900x. The
# money and the headline are unchanged; only the split between the table the
# player watches and the multiplier moves. high keeps its identity through
# RISK_SHAPES (top, beta, sub40), which is where it actually lives.
#
# Integer on purpose: lumen_pay rounds to 1dp, so a fractional boost like 2.5
# turns a 0.1x tier into 0.25x and silently rounds it, breaking the LUT's
# multiple-of-10-units rule at the smallest tiers.
LUMEN_BOOST = {
    "classic": 2.0,
    "low": 2.0,
    "medium": 2.0,
    "high": 2.0,
}
# Buy chips multiply Lumen by the chip cost, not the Earn ×2. Priced into the
# cost-unit solve so RTP stays on target: the advertised rows shrink, the
# catch still pays 10× / 100× the table. Earn is unchanged.
BUY_LUMEN_BOOST = {
    "buy10": 10.0,
    "buy100": 100.0,
}


def lumen_boost_for(risk: str, buy: str | None = None) -> float:
    """Lumen multiplier for this mode. Off never calls this (boost is 1)."""
    if buy is not None:
        return BUY_LUMEN_BOOST[buy]
    return LUMEN_BOOST[risk]


EXTRA_REASONS = ("none", "lumen", "near", "luck", "bought")
REASON_TO_EVENT = {
    "none": None,
    "lumen": "lumen",
    "near": "nearMiss",
    "luck": "natural",
    "bought": "bought",
}

_SPIN_RE = re.compile(
    r"^hits_(\d+)_lumen_([01])_extra_([01])_(none|lumen|near|luck|bought)_(\d+)"
    r"(?:_pulse_([01]))?$"
)


@dataclass(frozen=True)
class SpinCriteria:
    main_hits: int
    lumen_hit: bool
    extras: bool
    extra_reason: str
    extra_hits: int
    pulse: bool = False
    # Off pick_1 only: this book is one of the PICK_ONE_BONUS_WEIGHT misses that
    # pay PICK_ONE_BONUS above the advertised miss. Earn never sets it — its
    # lattice is already fine enough without a third tier.
    miss_bonus: bool = False

    @property
    def total_hits(self) -> int:
        return self.main_hits + self.extra_hits


#: Buy chips, and the stake multiple each costs. A buy round settles on the Earn
#: rules with the extras forced open, so `parse_mode_name` reports it as earn.
BUY_SUFFIXES = {"buy10": 10.0, "buy100": 100.0}

#: Both buy chips place the Lumen mark on one of the player's picks (including
#: pick_1). The mark is *not* forced into the ten: catch is hit-or-miss.
#: P(lumenHit) = 10/40 = 0.25 for every pick size; P(lumenHit | h) = h/k.
#: A full card (h=k) always catches. Hit on a paying row pays BUY_LUMEN_BOOST
#: (10× / 100×); a miss leaves the advertised base. Pulse ×2 still rolls on
#: 10% of bought-extra books. Dead rows stay dead.
#:
#: Sample space is C(40, k) · k · scale (ordinary hypergeometric × mark slots
#: among the k picks). This is not Earn: Earn marks one of the drawn ten.
GUARANTEED_LUMEN_BUYS = frozenset({"buy10", "buy100"})
MIN_PLACED_PICKS = 1


def lumen_placed_on_pick(buy: str | None, k: int) -> bool:
    """Whether this mode sits Lumen on a player pick (hit-or-miss, not forced)."""
    return buy in GUARANTEED_LUMEN_BUYS and k >= MIN_PLACED_PICKS


def parse_mode_name(name: str) -> tuple[str, int, bool, str | None]:
    """'{risk}_pick_{k}[_earn|_buy10|_buy100]' → (risk, k, earn, buy).

    `buy` is the chip name or None. Buy modes return earn=True because they
    settle through the Earn tables and bonus channels; the only differences are
    the cost and the forced extras, both of which the caller reads off `buy`.
    """
    buy = next((s for s in BUY_SUFFIXES if name.endswith(f"_{s}")), None)
    if buy is not None:
        core = name[: -(len(buy) + 1)]
        risk, pick = core.rsplit("_pick_", 1)
        return risk, int(pick), True, buy
    earn = name.endswith("_earn")
    core = name[: -5] if earn else name
    risk, pick = core.rsplit("_pick_", 1)
    return risk, int(pick), earn, None


def mode_name(risk: str, k: int, earn: bool = False, buy: str | None = None) -> str:
    base = f"{risk}_pick_{k}"
    if buy is not None:
        return f"{base}_{buy}"
    return f"{base}_earn" if earn else base


def off_outcomes(k: int, risk: str | None = None) -> list[SpinCriteria]:
    """Off books for `k` picks: one per hit count, plus the pick_1 bonus miss
    on risks that carry it (see PICK_ONE_BONUS_RISKS)."""
    out = [SpinCriteria(h, False, False, "none", 0) for h in range(k + 1)]
    if k == 1 and (risk is None or risk in PICK_ONE_BONUS_RISKS):
        out.insert(1, SpinCriteria(0, False, False, "none", 0, False, True))
    return out


def off_weight(k: int, spin: SpinCriteria, risk: str | None = None) -> int:
    """LUT weight for an Off book. pick_1's miss weight splits across two tiers
    on bonus risks; every other mode is a plain hypergeometric count."""
    weight = base_hit_weight(k, spin.main_hits)
    if k != 1 or spin.main_hits != 0:
        return weight
    if risk is not None and risk not in PICK_ONE_BONUS_RISKS:
        return weight
    return PICK_ONE_BONUS_WEIGHT if spin.miss_bonus else weight - PICK_ONE_BONUS_WEIGHT


def off_pay(spin: SpinCriteria, table: list[float]) -> float:
    """Off payout for a book, including pick_1's bonus miss tier."""
    base = (
        round(float(table[spin.main_hits] or 0), 1)
        if spin.main_hits < len(table)
        else 0.0
    )
    return round(base + PICK_ONE_BONUS, 1) if spin.miss_bonus else base


def base_hit_weight(
    k: int, h: int, drawn: int = DRAWN, rest: int = REST, placed: bool = False
) -> int:
    """Hypergeometric ways to realize `h` main hits on a `k`-pick card.

    `placed` (buy 10× / 100×): the mark sits on a pick but is not forced
    into the ten, so hit counts stay ordinary Hypergeometric(40, 10, k).
    Mark-slot multiplicity (`k`) lives in `lumen_hit_factor`, not here.
    """
    del placed  # draw side is the same; mark slots are in lumen_hit_factor
    if h < 0 or h > k or (k - h) > rest or h > drawn:
        return 0
    return comb(drawn, h) * comb(rest, k - h)


def pick_one_hit(miss: float) -> float:
    """Hit pay for the advertised Off pick_1 pair, on the 0.1x grid the RGS
    requires. This lands the pair on PICK_ONE_BASE_RTP, not RTP_TARGET — the
    remaining 1.5pp comes from the bonus miss tier."""
    return round((PICK_ONE_BASE_RTP - 0.75 * miss) / 0.25, 1)


def pick_one_row(risk: str) -> list[float]:
    """Off-mode advertised miss/hit (no Lumen)."""
    miss = PICK_ONE_MISS[risk]
    return [miss, pick_one_hit(miss)]


def has_pick_one_bonus(risk: str) -> bool:
    """Whether this risk's Off pick_1 carries the miss-bonus tier."""
    return risk in PICK_ONE_BONUS_RISKS


def pick_one_bonus_miss(risk: str) -> float:
    """The upgraded miss. Advertised alongside the plain one."""
    return round(PICK_ONE_MISS[risk] + PICK_ONE_BONUS, 1)


def pick_one_tiers(risk: str) -> list[tuple[int, float]]:
    """(weight, pay) over all 40 Off pick_1 books, in payout order."""
    miss, hit = pick_one_row(risk)
    if not has_pick_one_bonus(risk):
        return [(MISS_WEIGHT, miss), (HIT_WEIGHT, hit)]
    return [
        (MISS_WEIGHT - PICK_ONE_BONUS_WEIGHT, miss),
        (PICK_ONE_BONUS_WEIGHT, pick_one_bonus_miss(risk)),
        (HIT_WEIGHT, hit),
    ]


def pick_one_rtp(risk: str) -> float:
    tiers = pick_one_tiers(risk)
    total = sum(w for w, _ in tiers)
    return sum(w * pay for w, pay in tiers) / total


def pick_one_std(risk: str) -> float:
    tiers = pick_one_tiers(risk)
    total = sum(w for w, _ in tiers)
    mean = pick_one_rtp(risk)
    var = sum(w * (pay - mean) ** 2 for w, pay in tiers) / total
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
    if rest.endswith("_bonus_1"):
        hits_s = rest[: -len("_bonus_1")]
        if hits_s.isdigit():
            return SpinCriteria(int(hits_s), False, False, "none", 0, False, True)
    raise ValueError(f"cannot parse hits from criteria {criteria}")


def lumen_books_for_hits(
    hits: int, drawn: int = DRAWN, placed: bool = False, k: int = 0
) -> list[bool]:
    """Which lumenHit flags exist at this hit count.

    Default: the mark is one of the `drawn` numbers, so a partial catch still
    splits — some of those numbers are picks, some are not.

    `placed` (buy 10× / 100×): the mark is one of the k picks, not forced
    into the ten. h=0 never catches; h=k always catches; partial cards split.
    """
    if placed:
        if hits <= 0:
            return [False]
        if k > 0 and hits >= k:
            return [True]
        return [False, True]
    if hits <= 0:
        return [False]
    if hits >= drawn:
        return [True]
    return [False, True]


def lumen_hit_factor(
    hits: int, lumen_hit: bool, drawn: int = DRAWN, k: int = 0, placed: bool = False
) -> int:
    """How many marked-slot assignments realize this lumenHit flag.

    Default: the mark is one of the `drawn` numbers — `hits` of them are picks,
    so P(lumenHit | h) = h/drawn and the factor is `hits` or `drawn - hits`.

    `placed`: the mark is one of the k picks. P(lumenHit | h) = h/k, so a
    catch book has `hits` mark slots and a miss book has `k - hits`.
    """
    if placed:
        return hits if lumen_hit else max(k - hits, 0)
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


def paying_from_table(table: list[float]) -> frozenset[int]:
    return frozenset(h for h, value in enumerate(table) if float(value) > 0)


def extras_forced_reason(
    k: int,
    main_hits: int,
    lumen_hit: bool,
    paying: frozenset[int] | None = None,
    bought: bool = False,
) -> str | None:
    """Forced extras. Catching Lumen only opens if the main ten already pays.

    `paying` is advertised hit counts with a >0 row. None treats every hit as
    paying (old lumen-always-open behavior). A dead-table Lumen catch must not
    fall through to luck.

    `bought` is the buy chips: the two extras are what the purchase buys, so
    they open unconditionally and outrank every earned reason.
    """
    if bought:
        return "bought"
    if lumen_hit:
        if paying is None or main_hits in paying:
            return "lumen"
        return None
    if k >= 4 and main_hits == k - 1:
        return "near"
    return None


def extra_outcomes(
    k: int,
    main_hits: int,
    lumen_hit: bool,
    paying: frozenset[int] | None = None,
    bought: bool = False,
) -> list[tuple[bool, str, int]]:
    """Earn extras: first match lumen (paying main) → near-miss → luck.

    Luck weight is EXTRA_CHANCE_PCT[risk] / 100 of the leftover after Lumen
    and near-miss. It is 0 at pick_1 (cannot have two main hits). Catching
    Lumen on a 0× main row keeps extras closed and does not roll luck.
    """
    forced = extras_forced_reason(k, main_hits, lumen_hit, paying, bought)
    js = extra_hit_js(k, main_hits)
    if forced:
        return [(True, forced, j) for j in js]
    if lumen_hit:
        return [(False, "none", 0)]
    if main_hits >= 2:
        return [(False, "none", 0)] + [(True, "luck", j) for j in js]
    return [(False, "none", 0)]


def spin_outcomes(
    k: int,
    drawn: int = DRAWN,
    paying: frozenset[int] | None = None,
    bought: bool = False,
    placed: bool = False,
) -> list[SpinCriteria]:
    out: list[SpinCriteria] = []
    for main_hits in range(k + 1):
        for lumen_hit in lumen_books_for_hits(main_hits, drawn, placed, k):
            for extras, reason, extra_hits in extra_outcomes(
                k, main_hits, lumen_hit, paying, bought
            ):
                # Pulse is a charge on an extra light, so only extra-open books
                # split on it. A closed-extras round has no face to mount the
                # boost on and books exactly one outcome.
                for pulse in ((False, True) if extras else (False,)):
                    out.append(
                        SpinCriteria(main_hits, lumen_hit, extras, reason, extra_hits, pulse)
                    )
    return out


def book_count_for_picks(
    k: int,
    drawn: int = DRAWN,
    paying: frozenset[int] | None = None,
    bought: bool = False,
    placed: bool = False,
) -> int:
    return len(spin_outcomes(k, drawn, paying, bought, placed))


def hit_criteria_base(hits: int, miss_bonus: bool = False) -> str:
    return f"hits_{hits}_bonus_1" if miss_bonus else f"hits_{hits}"


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
    paying: frozenset[int] | None = None,
    bought: bool = False,
    placed: bool = False,
) -> int:
    base = (
        base_hit_weight(k, spin.main_hits, drawn, rest, placed)
        * lumen_hit_factor(spin.main_hits, spin.lumen_hit, drawn, k, placed)
    )
    pair_total = comb(rest, EXTRA_N)
    pair = extra_pair_weight(k, spin.main_hits, spin.extra_hits)
    chance = EXTRA_CHANCE_PCT[risk]
    # The Pulse split only exists on extra-open books; a closed-extras
    # round carries the full denominator because it never rolls.
    if spin.extras:
        pulse_pct = pulse_chance_pct(risk, k)
        pulse_part = (
            pulse_pct if spin.pulse else (CHANCE_DENOM - pulse_pct)
        )
    else:
        pulse_part = CHANCE_DENOM
    forced = extras_forced_reason(k, spin.main_hits, spin.lumen_hit, paying, bought)
    # Bought extras are certain, so they carry the whole CHANCE_DENOM rather
    # than a luck slice. Summed over extra_hits and pulse this still lands on
    # weight_total, so buy books validate against the same weight assertion.
    if bought:
        if not spin.extras:
            raise ValueError(f"bought extras closed: {spin}")
        return base * CHANCE_DENOM * pair * pulse_part
    if not spin.extras:
        if forced:
            raise ValueError(f"forced extras closed: {spin}")
        if spin.lumen_hit:
            extra_part = CHANCE_DENOM * pair_total
        elif spin.main_hits >= 2:
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


def lumen_pay(
    base: float, lumen_hit: bool, risk: str, buy: str | None = None, cost: float = 1.0
) -> float:
    """Table × Lumen. Catching does not rescue a 0× row.

    Rounds to 0.1× the *base bet* (LUT multiple-of-10), not 0.1 of whatever
    units `base` is in. Buy ladders are solved in cost units (0.001 of a 100×
    chip is 0.1× stake); rounding those to 1dp would snap them to 0 or 0.1 and
    destroy the RTP.
    """
    if lumen_hit and base > 0:
        amount = float(base) * lumen_boost_for(risk, buy)
    else:
        amount = float(base)
    return round(round(amount * cost, 1) / cost, 10)


def pulse_pay(
    amount: float, pulse: bool, risk: str, cost: float = 1.0
) -> float:
    """Paying table × Pulse. Pulse does not rescue a 0× row."""
    if pulse and amount > 0:
        amount = float(amount) * PULSE_BOOST[risk]
    return round(round(float(amount) * cost, 1) / cost, 10)


def settle_pay(
    base: float,
    lumen_hit: bool,
    pulse: bool,
    risk: str,
    buy: str | None = None,
    cost: float = 1.0,
) -> float:
    """Table × Lumen × Pulse. Neither bonus rescues a 0× row."""
    return pulse_pay(lumen_pay(base, lumen_hit, risk, buy, cost), pulse, risk, cost)


def lumen_boost_applied(
    base: float, lumen_hit: bool, risk: str, buy: str | None = None
) -> float:
    if lumen_hit and base > 0:
        return lumen_boost_for(risk, buy)
    return 1.0


def pulse_boost_applied(amount: float, pulse: bool, risk: str) -> float:
    if pulse and amount > 0:
        return PULSE_BOOST[risk]
    return 1.0


def weight_total(k: int, drawn: int = DRAWN, placed: bool = False) -> int:
    """Total book weight for `k` picks: every draw configuration × every mark slot.

    Default: C(40, k) cards × `drawn` mark slots among the ten.
    `placed`: C(40, k) cards × `k` mark slots among the player's picks.
    The marked pick is not forced into the ten.
    """
    if placed:
        return comb(POOL, k) * k * weight_scale()
    return comb(POOL, k) * drawn * weight_scale()


@lru_cache(maxsize=None)
def effective_coeff(
    risk: str,
    k: int,
    paying: frozenset[int],
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
) -> tuple[float, ...]:
    """RTP = sum_h coeff[h] * advertised[h] when advertised[h] > 0 iff h in paying.

    Lumen and Pulse are priced in: a paying row that is caught contributes
    boost * P; Pulse (×2 on every risk) on `pulse_chance_pct(risk, k)` of the
    books whose extras open — 10% on picks 2–10, a per-risk slice on pick_1
    so the advertised hit can follow Off's miss ladder. Closed-extras rounds
    never roll it. Extras from Lumen only open when main_hits is in `paying`.

    `bought` forces the extras open, which is the buy chips' whole product. It
    shifts weight into the higher total-hit buckets rather than adding a
    channel, so the coefficients stay a plain RTP decomposition.

    `placed` sits the mark on a pick (hit-or-miss; P(catch)=0.25).
    `buy` selects BUY_LUMEN_BOOST (10× / 100×) instead of Earn ×2.
    """
    total = weight_total(k, placed=placed)
    boost = lumen_boost_for(risk, buy)
    coeff = [0.0] * (k + 1)
    for spin in spin_outcomes(k, paying=paying, bought=bought, placed=placed):
        hits = spin.total_hits
        if hits not in paying:
            continue
        factor = boost if spin.lumen_hit else 1.0
        if spin.pulse:
            factor *= PULSE_BOOST[risk]
        coeff[hits] += (
            spin_weight(k, spin, risk, paying=paying, bought=bought, placed=placed)
            * factor
            / total
        )
    return tuple(coeff)


def settled_pairs(
    risk: str,
    k: int,
    table: list[float],
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
    cost: float = 1.0,
) -> list[tuple[int, float]]:
    """(weight, settled multiplier) for every spin book."""
    paying = paying_from_table(table)
    return [
        (
            spin_weight(k, spin, risk, paying=paying, bought=bought, placed=placed),
            settle_pay(
                table[spin.total_hits], spin.lumen_hit, spin.pulse, risk, buy, cost
            ),
        )
        for spin in spin_outcomes(k, paying=paying, bought=bought, placed=placed)
    ]


def settled_rtp(
    risk: str,
    k: int,
    table: list[float],
    bought: bool = False,
    placed: bool = False,
    buy: str | None = None,
    cost: float = 1.0,
) -> float:
    total = weight_total(k, placed=placed)
    return (
        sum(w * m for w, m in settled_pairs(risk, k, table, bought, placed, buy, cost))
        / total
    )


def settled_stats(
    risk: str,
    k: int,
    table: list[float],
    bought: bool = False,
    placed: bool = False,
    cost: float = 1.0,
    buy: str | None = None,
) -> dict:
    """Settled moments. `table` and `cost` must share a denomination.

    The solver grades buy ladders in *cost units* (then scales on export), so
    pass the chip cost there. Exported / dashboard tables are already in base-
    bet units — pass `cost=1`. Dashboard ETL>10k is 10,000× the base bet, so
    the cutoff in table units is `10000 / cost`. ETL sum is etl40 + etl10k
    and double-counts any win that clears both lines.
    """
    total = weight_total(k, placed=placed)
    pairs = settled_pairs(risk, k, table, bought, placed, buy, cost)
    rtp = sum(w * m for w, m in pairs) / total
    var = sum(w * (m - rtp) ** 2 for w, m in pairs) / total
    p5k = sum(w for w, m in pairs if m >= 5000) / total
    p10k = sum(w for w, m in pairs if m >= 10000) / total
    etl40 = sum(w * m for w, m in pairs if m >= 40) / total
    etl10k_cut = 10000.0 / cost
    etl10k = sum(w * m for w, m in pairs if m >= etl10k_cut) / total
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
        "etl_sum": etl40 + etl10k,
        "cvar": cvar,
        "max_m": max(m for _, m in pairs),
        "hit_rate": sum(w for w, m in pairs if m > 0) / total,
        "nonzero_payouts": sorted({m for _, m in pairs if m > 0}),
    }


def base_coeff(k: int) -> tuple[float, ...]:
    """Plain hypergeometric P(main hits = h). Off has no Lumen or Pulse to
    price in, so this is the Off counterpart of `effective_coeff`."""
    total = comb(POOL, k)
    return tuple(base_hit_weight(k, h) / total for h in range(k + 1))


def base_stats(k: int, table: list[float], risk: str | None = None) -> dict:
    """`settled_stats` over Off books: k+1 hit buckets, no bonus channels.

    Deliberately returns the same keys so `check_gates` can grade Off and Earn
    through one code path. `risk` scopes pick_1's miss-bonus tier.
    """
    total = comb(POOL, k)
    # Driven by off_outcomes rather than a range over hit counts so pick_1's
    # bonus miss tier is graded by the same code path as every other mode.
    # `risk` decides whether that tier exists (PICK_ONE_BONUS_RISKS).
    if risk is not None and k == 1:
        spins = off_outcomes(k, risk)
        pairs = [(off_weight(k, spin, risk), off_pay(spin, table)) for spin in spins]
    else:
        pairs = [(off_weight(k, spin), off_pay(spin, table)) for spin in off_outcomes(k)]
    pairs = [(w, m) for w, m in pairs if w > 0]
    rtp = sum(w * m for w, m in pairs) / total
    var = sum(w * (m - rtp) ** 2 for w, m in pairs) / total
    ranked = sorted(pairs, key=lambda t: t[1])
    cum = 0.0
    tail_start = ranked[0][1] if ranked else 0.0
    for w, m in ranked:
        cum += w / total
        if cum >= 0.999:
            tail_start = m
            break
    tail_p = sum(w for w, m in pairs if m >= tail_start) / total
    cvar = (
        sum(w * m for w, m in pairs if m >= tail_start) / total / tail_p
    ) if tail_p else 0.0
    etl40 = sum(w * m for w, m in pairs if m >= 40) / total
    etl10k = sum(w * m for w, m in pairs if m >= 10000) / total
    return {
        "rtp": rtp,
        "std": var**0.5,
        "p5k": sum(w for w, m in pairs if m >= 5000) / total,
        "p10k": sum(w for w, m in pairs if m >= 10000) / total,
        "etl40": etl40,
        "etl10k": etl10k,
        "etl_sum": etl40 + etl10k,
        "cvar": cvar,
        "max_m": max(m for _, m in pairs),
        "hit_rate": sum(w for w, m in pairs if m > 0) / total,
        "nonzero_payouts": sorted({m for _, m in pairs if m > 0}),
    }


@lru_cache(maxsize=None)
def pick_one_row_earn(risk: str) -> list[float]:
    """Earn advertised miss/hit so settled RTP (with Lumen) is ~RTP_TARGET.

    0.1x grid, unlike Off pick_1's 0.01x. Not a style choice: `lumen_pay` and
    `pulse_pay` round to 1dp, so a 0.01x advertised value is silently rounded at
    settlement and the row does not pay what the table says. Off has no such
    rounding, which is why it can use the finer grid to land exactly on target.

    Miss is pinned to Off's `PICK_ONE_MISS[risk]` so the four risks keep a
    visible hit ladder (low < classic < medium < high). Searching every miss
    and tie-breaking on `-miss` collapses them all onto 0.5/2.1 whenever
    Pulse chance is shared. Pulse chance is the remaining lever that puts
    each pinned miss on the 0.1× lattice inside MODE_RTP_BAND.
    """
    coeff = effective_coeff(risk, 1, frozenset({0, 1}))
    lo, hi = MODE_RTP_BAND
    best: tuple[float, float, list[float]] | None = None
    miss = PICK_ONE_MISS[risk]
    miss_i = int(round(miss * 10))
    for hit_i in range(miss_i + 1, 81):
        hit = hit_i / 10
        rtp = coeff[0] * miss + coeff[1] * hit
        if not lo <= rtp <= hi:
            continue
        err = abs(rtp - RTP_TARGET)
        table = [miss, hit]
        stats = settled_stats(risk, 1, table)
        if stats["std"] < STD_MIN:
            continue
        key = (err, -hit)
        if best is None or key < (best[0], -best[2][1]):
            best = (err, stats["std"], table)
    if best is None:
        raise ValueError(
            f"no pick_1 lattice for {risk} at miss={miss:g} with Lumen priced in"
        )
    return best[2]


def pick_one_std_earn(risk: str) -> float:
    return settled_stats(risk, 1, pick_one_row_earn(risk))["std"]


assert all(pick_one_std(risk) > STD_MIN for risk in PICK_ONE_MISS)
assert all(pick_one_std_earn(risk) > STD_MIN for risk in LUMEN_BOOST)
_EARN_PICK_ONE_HITS = [
    pick_one_row_earn(r)[1] for r in ("low", "classic", "medium", "high")
]
assert _EARN_PICK_ONE_HITS == sorted(_EARN_PICK_ONE_HITS) and len(set(_EARN_PICK_ONE_HITS)) == 4, (
    f"Earn pick_1 hits {_EARN_PICK_ONE_HITS} are not a strict hierarchy"
)
assert (
    abs(settled_rtp("classic", 1, pick_one_row_earn("classic")) - RTP_TARGET) <= 0.0025
)
# 1e-9 rather than exact equality: the sums are float, but the nearest reachable
# lattice point is 0.0025 away, so these still catch a genuine miss.
assert all(
    abs(0.75 * miss + 0.25 * pick_one_hit(miss) - PICK_ONE_BASE_RTP) < 1e-9
    for miss in PICK_ONE_MISS.values()
), "Off pick_1 advertised pair left its 0.025 lattice"
# Every Off pick_1 risk closes 0.950 -> 0.9650 with the miss-bonus tier.
assert all(
    abs(pick_one_rtp(risk) - RTP_TARGET) < 1e-9
    for risk in PICK_ONE_MISS
), "Off pick_1 bonus tier did not close the gap to target"
# base_stats grades Off through off_outcomes, so it must already see the third
# tier — this is what check_gates reads.
assert all(
    abs(base_stats(1, pick_one_row(risk), risk)["rtp"] - RTP_TARGET) < 1e-9
    for risk in PICK_ONE_MISS
), "base_stats missed Off pick_1's bonus tier"
# The bonus tier must not leak into any other mode, and pick_1's three books
# must still add up to the full C(40,1) sample space.
assert [s.miss_bonus for s in off_outcomes(1, "classic")] == [False, True, False]
assert [s.miss_bonus for s in off_outcomes(1, "low")] == [False, True, False]
assert [s.miss_bonus for s in off_outcomes(1, "medium")] == [False, True, False]
assert sum(off_weight(1, s, "classic") for s in off_outcomes(1, "classic")) == comb(POOL, 1)
assert sum(off_weight(1, s, "low") for s in off_outcomes(1, "low")) == comb(POOL, 1)
assert all(
    sum(off_weight(k, s) for s in off_outcomes(k)) == comb(POOL, k) for k in range(1, 11)
)
assert not any(s.miss_bonus for k in range(2, 11) for s in off_outcomes(k))
assert parse_spin_criteria("hits_0_bonus_1").miss_bonus
assert not parse_spin_criteria("hits_0").miss_bonus
# pick_1: 4 books, not 6. A closed-extras round books one outcome (no Pulse
# split), so each closed branch is 1 book and each open branch is 2.
assert book_count_for_picks(1) == 4
CLASSIC_8_PAYING = frozenset({3, 4, 5, 6, 7, 8})
assert extras_forced_reason(8, 2, True, CLASSIC_8_PAYING) is None
assert extra_outcomes(8, 2, True, CLASSIC_8_PAYING) == [(False, "none", 0)]
assert extras_forced_reason(8, 3, True, CLASSIC_8_PAYING) == "lumen"
assert extra_outcomes(8, 2, False, CLASSIC_8_PAYING)[0] == (False, "none", 0)
assert any(reason == "luck" for _, reason, _ in extra_outcomes(8, 2, False, CLASSIC_8_PAYING))
assert lumen_hit_factor(0, False) == 10
assert lumen_hit_factor(3, True) == 3
assert extra_pair_weight(5, 5, 0) == comb(REST, EXTRA_N)
assert extra_pair_weight(5, 4, 2) == 0
assert parse_spin_criteria("hits_3_lumen_1_extra_1_lumen_1_pulse_1") == SpinCriteria(
    3, True, True, "lumen", 1, True
)
assert lumen_pay(2.6, True, "classic") == 5.2
assert settle_pay(2.6, True, True, "classic") == 10.4
assert settle_pay(2.6, True, True, "medium") == 10.4
assert lumen_pay(0.088, False, "classic", cost=100) == 0.088
assert lumen_pay(0.088, True, "classic", "buy100", 100) == 8.8
assert settle_pay(0.088, True, True, "classic", "buy100", 100) == 17.6
assert lumen_pay(0.0, True, "high") == 0.0
assert pulse_pay(0.0, True, "medium") == 0.0
assert lumen_pay(2.6, False, "classic") == 2.6
assert lumen_boost_applied(0.0, True, "high") == 1.0
assert lumen_boost_applied(2.6, True, "medium") == 2.0
assert pulse_boost_applied(5.2, True, "classic") == 2.0
assert pulse_boost_applied(5.2, True, "medium") == 2.0
# Pulse only exists on extra-open books: no closed-extras book carries it, and
# within the open set it holds exactly that risk's PULSE_CHANCE_PCT.
assert not any(
    s.pulse for k in range(1, 11) for s in spin_outcomes(k) if not s.extras
)
assert all(
    abs(
        sum(spin_weight(k, s, r) for s in spin_outcomes(k) if s.pulse)
        / sum(spin_weight(k, s, r) for s in spin_outcomes(k) if s.extras)
        - pulse_chance_pct(r, k) / CHANCE_DENOM
    )
    < 1e-12
    for k in (1, 5, 10)
    for r in ("classic", "medium", "low", "high")
)
assert sum(spin_weight(1, spin, "classic") for spin in spin_outcomes(1)) == comb(40, 1) * DRAWN * weight_scale()
assert sum(spin_weight(5, spin, "classic") for spin in spin_outcomes(5)) == comb(40, 5) * DRAWN * weight_scale()
assert sum(
    spin_weight(8, spin, "classic", paying=CLASSIC_8_PAYING)
    for spin in spin_outcomes(8, paying=CLASSIC_8_PAYING)
) == comb(40, 8) * DRAWN * weight_scale()
# --- buy placed Lumen: mark on a pick, hit-or-miss ---------------------------
# Sample space is C(40, k) · k · scale (ordinary cards × mark among k picks).
assert all(
    sum(spin_weight(k, spin, r, bought=True, placed=True) for spin in spin_outcomes(k, bought=True, placed=True))
    == weight_total(k, placed=True)
    for k in range(MIN_PLACED_PICKS, 11)
    for r in ("classic", "high")
), "placed Lumen sample space is not C(40,k)·k"
assert all(
    weight_total(k, placed=True) == comb(POOL, k) * k * weight_scale()
    for k in range(MIN_PLACED_PICKS, 11)
), "placed weight_total is not C(40,k)·k·scale"
# Catch rate is 10/40 = 0.25 for every pick size (mark on a pick, not forced).
assert all(
    abs(
        sum(
            spin_weight(k, spin, r, bought=True, placed=True)
            for spin in spin_outcomes(k, bought=True, placed=True)
            if spin.lumen_hit
        )
        / weight_total(k, placed=True)
        - DRAWN / POOL
    )
    < 1e-12
    for k in range(MIN_PLACED_PICKS, 11)
    for r in ("classic", "medium")
), "placed Lumen catch rate is not 0.25"
# h=0 never catches; h=k always catches.
assert all(
    (not s.lumen_hit) if s.main_hits == 0 else True
    for k in range(MIN_PLACED_PICKS, 11)
    for s in spin_outcomes(k, bought=True, placed=True)
), "placed Lumen caught on a zero-hit card"
assert all(
    s.lumen_hit
    for k in range(MIN_PLACED_PICKS, 11)
    for s in spin_outcomes(k, bought=True, placed=True)
    if s.main_hits == k
), "placed Lumen missed a full card"
assert all(
    sum(base_hit_weight(k, h, placed=True) for h in range(k + 1)) == comb(POOL, k)
    for k in range(MIN_PLACED_PICKS, 11)
), "placed hit weights do not sum to C(40, k)"
assert lumen_hit_factor(3, True, k=5, placed=True) == 3
assert lumen_hit_factor(3, False, k=5, placed=True) == 2
assert lumen_books_for_hits(0, placed=True, k=5) == [False]
assert lumen_books_for_hits(1, placed=True, k=5) == [False, True]
assert lumen_books_for_hits(5, placed=True, k=5) == [True]
assert lumen_books_for_hits(1, placed=True, k=1) == [True]
# The flag is on for every buy pick size, off on Earn.
assert not lumen_placed_on_pick(None, 5)
assert lumen_placed_on_pick("buy10", 1) and lumen_placed_on_pick("buy10", 2)
assert lumen_placed_on_pick("buy100", 1) and lumen_placed_on_pick("buy100", 10)
assert lumen_boost_for("high") == 2.0
assert lumen_boost_for("high", "buy10") == 10.0
assert lumen_boost_for("high", "buy100") == 100.0
