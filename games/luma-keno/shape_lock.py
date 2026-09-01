"""Reusable ladder shape lock for every Lumen Keno paytable.

The solver used to close its RTP gap by pushing leftover return into whichever
body cell had the most probability mass. That produced neighbour cells the HUD
cannot tell apart (89.8 / 89.9 / 90.0, 1.9 / 2.0 / 2.1, 7.4 / 8.9 / 9.0) and
then a cliff into the jackpot (1.9 -> 350, 90 -> 4500). This module states the
column shape as executable constraints so that outcome is rejected at solve
time rather than discovered on a screenshot.

Applies to every Off / Earn / Buy x low / classic / medium / high x pick row.

The rules
---------
`increasing`     m[h_next] > m[h] on every paying pair.
`ratio_min`      m[h_next] / m[h] >= 1.25 after HUD rounding, so adjacent
                 paying cells are visibly different on the HUD.
`ratio_min_mid`  mid ladder pairs (both cells above the consolation line, not
                 the final catch) need >= 2.5, target 3.0-3.5. This is the rule
                 that forbids parking 7 and 8 on top of the hit that carries
                 the return.
`ratio_max`      <= 8.0 on every step except the final catch. One step may be
                 designated the volatility wall - the crossing from the
                 consolation block into the first celebrate cell - and that one
                 is allowed <= 18.0. Never 180.
`last_catch`     8.0 <= m[N] / m[N-1] <= 15.0 when N is the full card.
`no_mega_jump`   no step >= 20x outside the final catch (implied by ratio_max,
                 asserted separately so a future ratio_max edit cannot silently
                 re-open the cliff).
`consolation`    cells at or below 1x stay at or below 1x. A refund is not a
                 celebration (UKGC 14C).

Scope
-----
The ladder rules describe a *deep* column. `ratio_min_mid`, `ratio_max`,
`wall_ratio_max`, `no_mega_jump` and `last_catch` only apply from
`ladder_min_pick` (8) up, because below it there is no staircase to build: a
pick-2 row has two cells, and demanding an 8x final catch on it just pushes the
top out of the RTP window. Enforcing the deep rules fleet-wide marks almost
every short pick unreachable, which says the rule is mis-scoped rather than the
fleet broken. Shallow picks still owe `increasing`, `ratio_min`, `consolation`
and the lattice - which is what actually forbids 89.8 / 89.9 / 90.

`last_catch` additionally assumes the top is free to move. When it is pinned by
the absolute payout ceiling, set `last_catch_free=False`: a ratio floor under a
hard ceiling does not shape a ladder, it deletes the tier beneath the jackpot.

Nothing here targets losses-disguised-as-wins, near-miss density, or any other
misperception lever. The lock is about whether the printed column reads as a
designed curve; it does not move where the return sits between show and pay.

Denomination
------------
Rows are graded in their own units. Off rows are base-bet multiples and price
through `base_coeff`. Earn and Buy rows are *advertised* multiples that settle
through Lumen and Pulse, so they price through `effective_coeff` and their
advertised RTP is far below the settled RTP window. Pass the right coefficient
vector; the lock itself only reads the printed column.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction

GRID = 0.1
#: A paying cell at or below this is a refund, not a win.
CONSOLATION_MAX = 1.0
#: Shallowest pick that owes the full ladder rules. See "Scope" above.
LADDER_MIN_PICK = 8
INF = float("inf")


@dataclass(frozen=True)
class ShapeLock:
    """Ratio bounds for one paying column. Defaults are the shipped lock."""

    ratio_min: float = 1.25
    ratio_min_mid: float = 2.5
    ratio_mid_target: tuple[float, float] = (3.0, 3.5)
    ratio_max: float = 8.0
    #: Only the consolation -> celebrate crossing may use this.
    wall_ratio_max: float = 18.0
    last_catch_min: float = 8.0
    last_catch_max: float = 15.0
    #: Hard cliff ceiling outside the final catch.
    mega_jump: float = 20.0
    consolation_max: float = CONSOLATION_MAX
    grid: float = GRID
    #: Hits that must never pay. `m(0)=m(1)=m(2)=0` on the deep-pick rows.
    zero_prefix: tuple[int, ...] = field(default_factory=tuple)
    #: Shallowest pick that owes the ladder rules.
    ladder_min_pick: int = LADDER_MIN_PICK
    #: False when the top is pinned by the absolute payout ceiling, so the
    #: final catch cannot be moved to satisfy a ratio floor.
    last_catch_free: bool = True


LOCK = ShapeLock()


def scoped(lock: ShapeLock, k: int) -> ShapeLock:
    """The lock as it actually applies to a pick-`k` column.

    Relaxing here rather than at each call site means feasibility, the solver
    and the audit all read the same rules. Idempotent, so a caller that has
    already scoped a lock can pass it through again safely.
    """
    if k < lock.ladder_min_pick:
        # A short card has too few cells to carry a mid band - a pick-3 row has
        # two of them - so the mid floor drops to the plain step floor. The body
        # ceilings stay: a 184x jump between two paying cells is a cliff at any
        # depth, and dropping `ratio_max` here would pass the exact rows this
        # lock exists to catch. Only the final catch is freed, because an 8-15x
        # band on a shallow top is unsatisfiable against an ETL cap.
        return replace(
            lock,
            ratio_min_mid=lock.ratio_min,
            last_catch_min=lock.ratio_min,
            last_catch_max=INF,
        )
    if not lock.last_catch_free:
        # Jackpot pinned by the payout ceiling: the final catch is graded as an
        # ordinary step, so the tier below it is not forced under the stake.
        return replace(
            lock, last_catch_min=lock.ratio_min, last_catch_max=lock.ratio_max
        )
    return lock


def lock_for(
    cost: float = 1.0,
    *,
    pick: int | None = None,
    capped: bool = False,
    **overrides,
) -> ShapeLock:
    """Lock for a row designed in `cost` units.

    Buy chips are solved in cost units but published in base-bet multiples, and
    the published 0.1x lattice is a base-bet grid. A buy100 row therefore moves
    on a 0.001 grid in its own units. Everything else in the lock is a ratio
    and is denomination-free.

    Pass `pick` to get the depth-scoped lock, and `capped=True` when the top is
    held at the absolute payout ceiling.
    """
    lock = ShapeLock(grid=GRID / cost, last_catch_free=not capped, **overrides)
    return scoped(lock, pick) if pick is not None else lock


def paying_hits(row: list[float]) -> list[int]:
    return [h for h, m in enumerate(row) if m > 0]


def wall_step(row: list[float], lock: ShapeLock = LOCK) -> int | None:
    """Index h of the lower cell on the consolation -> celebrate crossing.

    Exactly one step can cross the 1x line, so the wall allowance cannot be
    spread across a ladder to launder several cliffs into one exception.
    """
    hits = paying_hits(row)
    for h, nxt in zip(hits, hits[1:]):
        if row[h] <= lock.consolation_max < row[nxt]:
            return h
    return None


def is_mid_pair(
    row: list[float], h: int, nxt: int, last: int, lock: ShapeLock = LOCK
) -> bool:
    """True when (h, nxt) is a mid-ladder pair that must stair, not pack.

    Mid means both cells are real wins (above the consolation line) and the
    pair is not the final catch. On 40/10 pick 10 this resolves to hits 5-8,
    which is where the leftover-RTP packing always landed.
    """
    if nxt == last:
        return False
    return row[h] > lock.consolation_max and row[nxt] > lock.consolation_max


def ratio_bounds(
    row: list[float], h: int, nxt: int, last: int, full_card: bool, lock: ShapeLock
) -> tuple[float, float]:
    """(min, max) allowed for m[nxt] / m[h]."""
    if nxt == last and full_card:
        return lock.last_catch_min, lock.last_catch_max
    lo = lock.ratio_min_mid if is_mid_pair(row, h, nxt, last, lock) else lock.ratio_min
    hi = lock.wall_ratio_max if h == wall_step(row, lock) else lock.ratio_max
    return lo, hi


def violations(
    row: list[float],
    k: int,
    *,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
    label: str = "",
) -> list[str]:
    """Every way `row` breaks the lock. Empty list means the column is clean.

    `full_card` is True when hit k is catching every pick, which is the only
    place a jackpot-sized final step is allowed.
    """
    lock = scoped(lock, k)
    tag = f"{label} " if label else ""
    out: list[str] = []

    if len(row) != k + 1:
        out.append(f"{tag}row length {len(row)} != {k + 1}")
        return out

    for h in lock.zero_prefix:
        if h <= k and row[h] != 0.0:
            out.append(f"{tag}h{h}: {row[h]} must not pay")

    for h, m in enumerate(row):
        # Tolerance scales with the grid: a buy100 row moves on 0.001 in its own
        # units, and 0.006 is only "off lattice" if you test it against 0.1.
        if m and abs(m / lock.grid - round(m / lock.grid)) > 1e-6:
            out.append(f"{tag}h{h}: {m} off the {lock.grid:g}x lattice")

    hits = paying_hits(row)
    if not hits:
        out.append(f"{tag}no paying cell")
        return out
    last = hits[-1]

    for h, nxt in zip(hits, hits[1:]):
        lo_m, hi_m = row[h], row[nxt]
        if hi_m <= lo_m:
            out.append(f"{tag}h{h}->h{nxt}: {lo_m} -> {hi_m} not increasing")
            continue
        ratio = hi_m / lo_m
        lo_r, hi_r = ratio_bounds(row, h, nxt, last, full_card, lock)
        kind = (
            "last-catch"
            if (nxt == last and full_card)
            else "mid"
            if is_mid_pair(row, h, nxt, last, lock)
            else "wall"
            if h == wall_step(row, lock)
            else "step"
        )
        if ratio < lo_r - 1e-9:
            out.append(
                f"{tag}h{h}->h{nxt}: {lo_m:g} -> {hi_m:g} ratio {ratio:.2f} "
                f"< {lo_r} ({kind}); cells are not visibly different"
            )
        if ratio > hi_r + 1e-9:
            out.append(
                f"{tag}h{h}->h{nxt}: {lo_m:g} -> {hi_m:g} ratio {ratio:.2f} "
                f"> {hi_r} ({kind}); cliff"
            )
        if not (nxt == last and full_card) and ratio >= lock.mega_jump:
            out.append(
                f"{tag}h{h}->h{nxt}: ratio {ratio:.2f} >= {lock.mega_jump} "
                "outside the final catch"
            )
    return out


def assert_shape(
    row: list[float],
    k: int,
    *,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
    label: str = "",
) -> None:
    """Raise on any lock violation. Call this from every chart's `_validate`."""
    errs = violations(row, k, full_card=full_card, lock=lock, label=label)
    if errs:
        raise AssertionError("shape lock: " + "; ".join(errs))


def rtp_of(coeff: tuple[float, ...] | list[float], row: list[float]) -> Fraction:
    """Exact RTP so a 1e-9 float drift cannot creep past the window check."""
    return sum(
        Fraction(str(c)) * Fraction(str(m)) for c, m in zip(coeff, row) if m
    )


def ev_shares(
    coeff: tuple[float, ...] | list[float], row: list[float]
) -> list[tuple[int, float]]:
    """(hit, share of return) for every paying cell. Names the RTP engine."""
    total = float(rtp_of(coeff, row))
    if not total:
        return []
    return [(h, coeff[h] * m / total) for h, m in enumerate(row) if m]


def ratios_of(row: list[float]) -> list[tuple[int, int, float]]:
    hits = paying_hits(row)
    return [(h, n, row[n] / row[h]) for h, n in zip(hits, hits[1:])]


# --------------------------------------------------------------------------
# Feasibility: can a frozen top host a lock-clean ladder at all?
# --------------------------------------------------------------------------


def _lowest_legal_below(v_next: float, wall_ok: bool, lock: ShapeLock) -> float:
    """Smallest cell that may legally sit under `v_next`.

    The wall allowance only exists on the consolation -> celebrate crossing, so
    it is offered only when using it actually lands the lower cell at or below
    the consolation line. Otherwise a ladder could claim the exception for an
    ordinary mid step and re-open the cliff the lock exists to close.
    """
    floor = max(lock.grid, v_next / lock.ratio_max)
    if wall_ok:
        walled = v_next / lock.wall_ratio_max
        if walled <= lock.consolation_max < v_next:
            floor = max(lock.grid, walled)
    return floor


def _highest_legal_below(v_next: float, lock: ShapeLock) -> float:
    """Largest cell that may legally sit under `v_next`.

    A pair only has to clear the 2.5x mid rule when *both* cells are real wins.
    When the wide-open 1.25x step would itself land above the consolation line,
    the pair becomes a mid pair and the tighter rule applies - except that the
    lower cell can always retreat to exactly the consolation line and stay a
    refund, which is often the higher of the two options.
    """
    loose = v_next / lock.ratio_min
    if loose <= lock.consolation_max:
        return loose
    return max(v_next / lock.ratio_min_mid, lock.consolation_max)


def feasible_rtp_range(
    coeff: tuple[float, ...] | list[float],
    hits: list[int],
    top: float,
    *,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
) -> tuple[float, float]:
    """(min, max) RTP reachable by any lock-clean ladder with this top.

    The minimum takes every step at its widest legal ratio, pushing the body as
    low as the lock allows; the maximum takes every step at its narrowest. If
    the designed RTP window falls outside this range, the frozen top and the
    lock cannot both hold, and something has to give - that is a decision for
    Ops, not something to paper over by packing neighbours.

    Both bounds are exact for the continuous relaxation, so a window inside the
    range still has to clear the 0.1x lattice; a window outside it is
    definitively unreachable.

    `lock` must already be depth-scoped - build it with `lock_for(pick=k)` - or
    a short pick is measured against ladder rules it does not owe.
    """
    n = len(hits)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        ev = coeff[hits[0]] * top
        return ev, ev

    lo_row = [0.0] * n
    hi_row = [0.0] * n
    lo_row[-1] = hi_row[-1] = top
    for i in range(n - 2, -1, -1):
        is_last_step = i == n - 2 and full_card
        if is_last_step:
            lo_row[i] = max(lock.grid, lo_row[i + 1] / lock.last_catch_max)
            hi_row[i] = max(lock.grid, hi_row[i + 1] / lock.last_catch_min)
        else:
            lo_row[i] = _lowest_legal_below(lo_row[i + 1], True, lock)
            hi_row[i] = _highest_legal_below(hi_row[i + 1], lock)

    lo = sum(coeff[h] * m for h, m in zip(hits, lo_row))
    hi = sum(coeff[h] * m for h, m in zip(hits, hi_row))
    return lo, hi


def min_top_for(
    hits: list[int],
    *,
    floor: float | None = None,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
) -> float:
    """Smallest top that can sit above these cells without packing them.

    A top below this forces neighbours together no matter how the return is
    distributed - the structural version of the 1.9 / 2.0 / 2.1 bug.
    """
    steps = len(hits) - 1
    if steps < 1:
        return lock.grid
    v = lock.grid if floor is None else floor
    for i in range(steps):
        if i == steps - 1 and full_card:
            v *= lock.last_catch_min
        elif v > lock.consolation_max:
            v *= lock.ratio_min_mid
        else:
            v *= lock.ratio_min
    return v


# --------------------------------------------------------------------------
# Solver: search the lock-clean ladders and pick the best-shaped one
# --------------------------------------------------------------------------


def _shape_score(row: list[float], hits: list[int], last: int, lock: ShapeLock) -> float:
    """Lower is better. Rewards mid ratios inside the 3.0-3.5 target band."""
    lo_t, hi_t = lock.ratio_mid_target
    score = 0.0
    for h, nxt in zip(hits, hits[1:]):
        ratio = row[nxt] / row[h]
        if is_mid_pair(row, h, nxt, last, lock):
            if ratio < lo_t:
                score += (lo_t - ratio) ** 2
            elif ratio > hi_t:
                score += (ratio - hi_t) ** 2 * 0.25
    return score


def _tail_ev_bounds(
    coeff: tuple[float, ...] | list[float],
    hits: list[int],
    full_card: bool,
    lock: ShapeLock,
) -> tuple[list[float], list[float]]:
    """Linear bounds on the EV still to come, per position, in the mid regime.

    From a value v at position i, the EV of positions i+1..n-1 lies in
    [v * lo[i], v * hi[i]]. Once a cell is above the consolation line every
    later step is a mid step, so the minimum ratio is 2.5 rather than 1.25 -
    which is what makes this bound tight enough to prune with. A ladder that
    is still in consolation gets the loose bound.
    """
    n = len(hits)
    lo = [0.0] * n
    hi = [0.0] * n
    for i in range(n - 2, -1, -1):
        is_last_step = i == n - 2 and full_card
        r_lo = lock.last_catch_min if is_last_step else lock.ratio_min_mid
        r_hi = lock.last_catch_max if is_last_step else lock.ratio_max
        c = coeff[hits[i + 1]]
        lo[i] = r_lo * (c + lo[i + 1])
        hi[i] = r_hi * (c + hi[i + 1])
    return lo, hi


def _propagate(
    hits: list[int],
    top: float,
    full_card: bool,
    lock: ShapeLock,
) -> tuple[list[float], list[float]]:
    """Per-cell [lo, hi] domains implied by the ratio rules and the fixed top.

    Pure interval arithmetic to a fixpoint. Cuts the search space before a
    single candidate is enumerated - most of the ladder is pinned by the top
    plus the last-catch rule alone.
    """
    n = len(hits)
    lo = [lock.grid] * n
    hi = [top] * n
    lo[-1] = hi[-1] = top
    for _ in range(n + 2):
        for i in range(n - 2, -1, -1):
            is_last = i == n - 2 and full_card
            r_lo = lock.last_catch_min if is_last else lock.ratio_min
            r_hi = lock.last_catch_max if is_last else lock.wall_ratio_max
            lo[i] = max(lo[i], lo[i + 1] / r_hi)
            hi[i] = min(hi[i], hi[i + 1] / r_lo)
        for i in range(n - 1):
            is_last = i == n - 2 and full_card
            r_lo = lock.last_catch_min if is_last else lock.ratio_min
            r_hi = lock.last_catch_max if is_last else lock.wall_ratio_max
            lo[i + 1] = max(lo[i + 1], lo[i] * r_lo)
            hi[i + 1] = min(hi[i + 1], hi[i] * r_hi)
    return lo, hi


def _candidates(
    lo: float, hi: float, coeff: float, window: float, grid: float, cap: int
) -> list[float]:
    """Grid values in [lo, hi], thinned geometrically when they cannot matter.

    A cell whose entire domain moves RTP by less than the window width is not a
    tuning lever, so enumerating it at full lattice resolution only multiplies
    the search. Those cells get a geometric sample instead, which also spreads
    them across the ladder rather than bunching them - the opposite of the
    packing this module exists to stop. Cells that *are* levers keep every
    lattice point, which is why callers must clamp `hi` by the RTP budget
    first: an unclamped domain would make even a lever look unaffordable to
    enumerate.
    """
    lo_t = max(1, int(round(lo / grid)))
    hi_t = int(hi / grid + 1e-9)
    if hi_t < lo_t:
        return []
    span = hi_t - lo_t + 1
    # A cell that can move RTP across the whole window on its own is a tuning
    # lever and keeps every lattice point; thinning one of these is how a
    # search convinces itself a solvable chart is impossible.
    if coeff * (hi - lo) > window or span <= cap:
        return [round(t * grid, 10) for t in range(lo_t, hi_t + 1)]
    ratio = (hi_t / lo_t) ** (1.0 / max(1, cap - 1))
    out: list[float] = []
    t = float(lo_t)
    while t <= hi_t + 0.5 and len(out) < cap:
        val = round(int(round(t)) * grid, 10)
        if not out or val > out[-1]:
            out.append(val)
        t = t * ratio if ratio > 1.0 else t + 1
    top_val = round(hi_t * grid, 10)
    if out and out[-1] != top_val:
        out.append(top_val)
    return out


def _snap(v: float, grid: float) -> float:
    # A relaxed short-pick lock leaves ratio ceilings at infinity, so a bound
    # can arrive unbounded; snapping that is a crash, not a wide search.
    if v == INF:
        return INF
    return round(round(v / grid) * grid, 10)


def _legal_bounds(
    row: list[float], hits: list[int], i: int, full_card: bool, lock: ShapeLock
) -> tuple[float, float]:
    """[lo, hi] for cell `i` with its two neighbours held fixed."""
    n = len(hits)
    lo, hi = lock.grid, INF
    if i > 0:
        below = row[hits[i - 1]]
        is_last = full_card and i == n - 1
        r_lo = lock.last_catch_min if is_last else lock.ratio_min
        r_hi = lock.last_catch_max if is_last else lock.wall_ratio_max
        if not is_last and below > lock.consolation_max:
            r_lo = lock.ratio_min_mid
            r_hi = lock.ratio_max
        lo = max(lo, below * r_lo)
        hi = min(hi, below * r_hi)
    if i < n - 1:
        above = row[hits[i + 1]]
        is_last = full_card and i == n - 2
        r_lo = lock.last_catch_min if is_last else lock.ratio_min
        r_hi = lock.last_catch_max if is_last else lock.wall_ratio_max
        lo = max(lo, above / r_hi)
        hi = min(hi, above / r_lo)
        if not is_last:
            # If this cell would sit above the consolation line, the pair above
            # becomes a mid pair and the tighter rule applies.
            mid_hi = above / lock.ratio_min_mid
            if mid_hi > lock.consolation_max:
                hi = min(hi, mid_hi)
            else:
                hi = min(hi, max(mid_hi, lock.consolation_max))
    if hi == INF:
        # Only reachable on the top cell of a relaxed short-pick lock. The top
        # is frozen by the caller, so any finite ceiling here is unused; the row
        # top keeps the bound honest rather than leaving it unbounded.
        hi = max(row[hits[-1]], lo)
    return lo, hi


def _repair_rtp(
    coeff: tuple[float, ...] | list[float],
    k: int,
    row: list[float],
    hits: list[int],
    rtp_window: tuple[float, float],
    full_card: bool,
    lock: ShapeLock,
) -> list[float] | None:
    """Walk `row` into the RTP window without breaking the lock.

    Cells are spent coarsest-first, like digits of a positional number: the
    high-mass cell sets the magnitude, the thin cells close the remainder. The
    remainder therefore lands where it is invisible, instead of being dumped on
    the neighbours of the hit that carries the return.
    """
    lo_w, hi_w = rtp_window
    target = 0.5 * (lo_w + hi_w)
    order = sorted(range(len(hits)), key=lambda i: -coeff[hits[i]])
    row = list(row)
    for _ in range(6):
        for i in order:
            h = hits[i]
            c = coeff[h]
            if c <= 0:
                continue
            rtp = float(rtp_of(coeff, row))
            if lo_w <= rtp <= hi_w:
                break
            lo, hi = _legal_bounds(row, hits, i, full_card, lock)
            if full_card and i == len(hits) - 1:
                continue  # the top is frozen
            want = row[h] + (target - rtp) / c
            new = min(max(_snap(want, lock.grid), _snap(lo + lock.grid / 2, lock.grid)),
                      _snap(hi - lock.grid / 2, lock.grid))
            if new <= 0 or new == row[h]:
                continue
            keep = row[h]
            row[h] = new
            if violations(row, k, full_card=full_card, lock=lock):
                row[h] = keep
        rtp = float(rtp_of(coeff, row))
        if lo_w <= rtp <= hi_w and not violations(
            row, k, full_card=full_card, lock=lock
        ):
            return row
    return None


def _polish(
    coeff: tuple[float, ...] | list[float],
    k: int,
    row: list[float],
    hits: list[int],
    rtp_window: tuple[float, float],
    full_card: bool,
    lock: ShapeLock,
    reach: int = 4,
) -> list[float]:
    """Nudge single cells to improve shape while staying in the window."""
    lo_w, hi_w = rtp_window
    last = hits[-1]
    best = list(row)
    best_score = _shape_score(best, hits, last, lock)
    improved = True
    while improved:
        improved = False
        for i in range(len(hits) - (1 if full_card else 0)):
            h = hits[i]
            for d in range(-reach, reach + 1):
                if d == 0:
                    continue
                trial = list(best)
                trial[h] = round(trial[h] + d * lock.grid, 10)
                if trial[h] <= 0:
                    continue
                rtp = float(rtp_of(coeff, trial))
                if not (lo_w <= rtp <= hi_w):
                    continue
                if violations(trial, k, full_card=full_card, lock=lock):
                    continue
                score = _shape_score(trial, hits, last, lock)
                if score < best_score - 1e-12:
                    best, best_score, improved = trial, score, True
    return best


def solve_row(
    coeff: tuple[float, ...] | list[float],
    k: int,
    hits: list[int],
    top: float,
    rtp_window: tuple[float, float],
    *,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
    max_nodes: int = 3_000_000,
    branch_cap: int = 26,
) -> list[float] | None:
    """Best-shaped lock-clean row on the lattice landing inside `rtp_window`.

    Ladders are *constructed*, not searched cell by cell. Each candidate is a
    geometric climb from a chosen first paying cell to the frozen top, with the
    final catch pulled out as its own step, so every candidate already reads as
    a designed curve before RTP is considered. Only then is the row walked into
    the RTP window, spending the coarsest cell first and closing the remainder
    on cells too thin to pin their neighbours.

    That ordering is the whole point. The old behaviour pushed leftover return
    onto whichever body cell held the most probability mass, which is exactly
    the cell whose neighbours then flatten against it on the HUD.

    Returns None when no lock-clean ladder reaches the window. Cross-check that
    against `feasible_rtp_range`: if the window sits outside the reachable
    band, the frozen top and the lock genuinely cannot both hold.
    """
    lock = scoped(lock, k)
    lo_w, hi_w = rtp_window
    n = len(hits)
    if n == 0:
        return None
    if n == 1:
        row = [0.0] * (k + 1)
        row[hits[0]] = top
        return row if lo_w <= coeff[hits[0]] * top <= hi_w else None

    last = hits[-1]
    dom_lo, dom_hi = _propagate(hits, top, full_card, lock)
    if any(dom_lo[i] > dom_hi[i] + 1e-12 for i in range(n)):
        return None

    steps = n - 1
    mid_steps = steps - 1 if full_card else steps
    best: tuple[float, list[float]] | None = None

    seed_lo = max(lock.grid, dom_lo[0])
    seed_hi = min(dom_hi[0], hi_w / coeff[hits[0]] if coeff[hits[0]] else dom_hi[0])
    lo_t, hi_t = int(seed_lo / lock.grid), int(seed_hi / lock.grid + 1e-9)
    if hi_t < lo_t:
        return None
    # Keep the seed scan bounded on fine lattices (buy chips run at 0.001).
    seed_step = max(1, (hi_t - lo_t + 1) // 400)

    # An unbounded last catch means the top is not held in a band, so there is
    # nothing to sweep: the cell below it is placed by the body rules instead.
    last_span = lock.last_catch_max - lock.last_catch_min
    last_ratios = (
        [lock.last_catch_min + i * 0.5 for i in range(int(last_span / 0.5) + 1)]
        if full_card and last_span != INF
        else [1.0]
    )

    found: list[tuple[float, list[float]]] = []
    for t0 in range(lo_t, hi_t + 1, seed_step):
        m0 = round(t0 * lock.grid, 10)
        for r_last in last_ratios:
            end = top / r_last if full_card else top
            if end <= m0 or mid_steps <= 0:
                continue
            r = (end / m0) ** (1.0 / mid_steps)
            if r < lock.ratio_min - 1e-9 or r > lock.wall_ratio_max + 1e-9:
                continue
            row = [0.0] * (k + 1)
            row[hits[0]] = m0
            v = m0
            for i in range(1, mid_steps + 1):
                v *= r
                row[hits[i]] = max(_snap(v, lock.grid), lock.grid)
            row[last] = top
            fixed = _repair_rtp(coeff, k, row, hits, rtp_window, full_card, lock)
            if fixed is not None:
                found.append((_shape_score(fixed, hits, last, lock), fixed))

    if not found:
        return None
    # Polish only the strongest few: the hill-climb is the expensive part and
    # a badly shaped seed does not become the best row by being nudged.
    found.sort(key=lambda t: t[0])
    for _, row in found[:6]:
        polished = _polish(coeff, k, row, hits, rtp_window, full_card, lock)
        score = _shape_score(polished, hits, last, lock)
        if best is None or score < best[0]:
            best = (score, polished)
    return best[1] if best else None


def describe(
    coeff: tuple[float, ...] | list[float],
    row: list[float],
    k: int,
    *,
    full_card: bool = True,
    lock: ShapeLock = LOCK,
) -> str:
    """One-line audit: cells, RTP, adjacent ratios, RTP engine."""
    cells = " / ".join(f"{m:g}" for m in row if m)
    rtp = float(rtp_of(coeff, row))
    rats = " ".join(f"{h}->{n}:{r:.2f}" for h, n, r in ratios_of(row))
    shares = ev_shares(coeff, row)
    engine = max(shares, key=lambda t: t[1]) if shares else (0, 0.0)
    errs = violations(row, k, full_card=full_card, lock=lock)
    return (
        f"[{cells}] rtp={rtp:.6f} engine=h{engine[0]}@{engine[1] * 100:.1f}% "
        f"ratios {rats} {'CLEAN' if not errs else 'VIOLATIONS: ' + '; '.join(errs)}"
    )
