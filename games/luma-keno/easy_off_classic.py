"""Off `classic` — max-anchored geometric ladder, pick_10 max 1000x.

Deterministic algorithm, per pick (Off only, no bonus channels):

1. Lock M = designed max (ladder tops at 1000x on pick_10).
2. Keep the HUD zero prefix (same first paying hit f).
3. Shape: every paying cell grows by the SAME factor toward the peak:
       m[h] = m_f * r^(h-f),   r = (M / m_f)^(1/(k-f))
4. Solve m_f from Σ P(h)·m[h] = 0.9650. Monotone in m_f, so bisection
   converges to a unique answer (2 paying cells: closed form
   m_f = (0.9650 - P(k)*M) / P(f)).
5. Snap to the 0.1x lattice (max kept exact), fix monotonicity.
6. Deterministic repair: coordinate descent in a fixed order (cells sorted
   by RTP leverage), ±0.1..0.3 nudges accepted only if they strictly
   improve |RTP - 0.9650| while keeping the progressive ratio inside a
   band of the ideal r. Same input → same matrix, every run.

Pick 2 exception: HUD max 5.0 has no in-window lattice point
(1.7/5.0 = 0.9423, 1.8/5.0 = 0.9808). Snap is 5.4, same exception Easy
took at 4.5 → 4.7.

pick_1 stays on the advertised pair [0.4, 2.6] in keno_pick_one.py
(base RTP 0.950) plus the 1-in-5 miss-bonus third tier so LUT RTP is
0.9650. Not in CLASSIC_OFF.

Scope: **Off only.** Earn `classic` and the buy chips keep their own ladders.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import (
    MODE_RTP_BAND,
    STD_MIN,
    base_coeff,
    base_stats,
)

RTP_WINDOW = (0.9630, 0.9655)

#: Competitor Classic HUD rows: zeros/shape template only.
CLASSIC_HUD = {
    2: [0.00, 1.50, 5.00],
    3: [0.00, 0.00, 2.50, 40.00],
    4: [0.00, 0.00, 1.50, 9.00, 100.0],
    5: [0.00, 0.00, 1.10, 4.00, 10.00, 300.0],
    6: [0.00, 0.00, 0.00, 2.00, 9.00, 100.0, 500.0],
    7: [0.00, 0.00, 0.00, 1.10, 3.00, 9.00, 100.0, 600.0],
    8: [0.00, 0.00, 0.00, 1.50, 3.00, 9.00, 40.00, 200.0, 750.0],
    9: [0.00, 0.00, 0.00, 1.10, 1.50, 3.00, 5.00, 50.00, 400.0, 900.0],
    10: [0.00, 0.00, 0.00, 1.10, 1.50, 2.00, 4.00, 10.00, 50.00, 500.0, 1000.0],
}

#: Designed max ladder. Strictly increasing, top = 1000x on pick_10.
#: Perfect-hit tops on picks 3-6 cut twice (HUD 40/100/300/500 was too big):
#: 26.5/49.5/150/400 -> 17.5/30/75/200. Pick 3 lattice only admits
#: 8.5/13/17.5/22/26.5...; 17.5 is the last step that still reads as a peak
#: (13x is only 2.2x the hit-2 cell).
MAX_LADDER = {
    2: 5.4,
    3: 17.5,
    4: 30.0,
    5: 75.0,
    6: 200.0,
    7: 600.0,
    8: 750.0,
    9: 900.0,
    10: 1000.0,
}

TARGET = Fraction(965, 1000)
WINDOW = (Fraction(963, 1000), Fraction(9655, 10000))
EPS = 1e-9
RATIO_BANDS = (2.5, 4.0, 8.0)


def _probs(k: int) -> list[Fraction]:
    return [Fraction(str(c)) for c in base_coeff(k)]


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(p * Fraction(str(m)) for p, m in zip(_probs(k), row))


def _first_paying(hud: list[float]) -> int:
    return next(h for h, m in enumerate(hud) if m > 0)


def _paying(hud: list[float], k: int) -> list[int]:
    return [h for h in range(k + 1) if hud[h] > 0]


def _row_from(f: int, k: int, m_f: float, r: float, mx: float) -> list[float]:
    row = [0.0] * (k + 1)
    for i in range(k - f + 1):
        row[f + i] = m_f * r**i
    row[k] = mx
    return row


def _seed_geometric(k: int, hud: list[float], mx: float) -> tuple[list[float], float]:
    """Solve m_f so the constant-ratio ladder from m_f to mx hits 0.9650."""
    f = _first_paying(hud)
    steps = k - f
    probs = [float(p) for p in _probs(k)]
    target = float(TARGET)
    if steps == 0:
        # Single paying cell: the max is the whole row (Hard pick 2).
        return _row_from(f, k, mx, 1.0, mx), 1.0
    if steps == 1:
        m_f = (target - probs[k] * mx) / probs[f]
        return _row_from(f, k, m_f, mx / m_f, mx), mx / m_f

    def rtp_of(m_f: float) -> float:
        r = (mx / m_f) ** (1.0 / steps)
        row = _row_from(f, k, m_f, r, mx)
        return sum(probs[h] * row[h] for h in range(k + 1))

    lo, hi = mx * 1e-6, mx * 0.999
    for _ in range(200):
        mid = (lo + hi) / 2
        if rtp_of(mid) < target:
            lo = mid
        else:
            hi = mid
    m_f = (lo + hi) / 2
    r = (mx / m_f) ** (1.0 / steps)
    return _row_from(f, k, m_f, r, mx), r


def _snap(k: int, hud: list[float], seed: list[float], mx: float) -> list[float]:
    row = [0.0] * (k + 1)
    for h in range(k + 1):
        if hud[h] > 0 and h != k:
            row[h] = float(int(seed[h] * 10 + 0.5)) / 10
    row[k] = mx
    for h in range(1, k + 1):
        if hud[h] > 0 and row[h] <= row[h - 1]:
            row[h] = round(row[h - 1] + 0.1, 1)
    for h in range(k - 1, _first_paying(hud) - 1, -1):
        if hud[h] > 0 and row[h] >= row[h + 1]:
            row[h] = round(row[h + 1] - 0.1, 1)
    return row


def _shape_ok(
    k: int,
    hud: list[float],
    row: list[float],
    mx: float,
    r_ideal: float,
    band: float,
) -> bool:
    if len(row) != k + 1 or max(row) != mx:
        return False
    if any(abs(m * 10 - round(m * 10)) > EPS for m in row if m):
        return False
    if [m == 0 for m in row] != [m == 0 for m in hud]:
        return False
    cells = [row[h] for h in _paying(hud, k)]
    if not all(b > a for a, b in zip(cells, cells[1:])):
        return False
    lo_r, hi_r = max(1.1, r_ideal / band), r_ideal * band
    return all(lo_r - EPS <= b / a <= hi_r + EPS for a, b in zip(cells, cells[1:]))


def _legal(k: int, hud: list[float], row: list[float], mx: float) -> bool:
    rtp = _exact_rtp(k, row)
    if not (WINDOW[0] <= rtp <= WINDOW[1]):
        return False
    stats = base_stats(k, row)
    return (
        stats["std"] >= STD_MIN
        and stats["hit_rate"] >= 0.021
        and stats["etl_sum"] <= 1.45
    )


def _score(k: int, hud: list[float], row: list[float], mx: float) -> tuple:
    return (
        0 if _legal(k, hud, row, mx) else 1,
        abs(_exact_rtp(k, row) - TARGET),
    )


def _repair(
    k: int,
    hud: list[float],
    row: list[float],
    mx: float,
    r_ideal: float,
    band: float,
) -> list[float] | None:
    """Deterministic coordinate descent: fixed cell order, fixed deltas."""
    probs = _probs(k)
    body = [h for h in _paying(hud, k) if h != k]
    order = sorted(body, key=lambda h: (-probs[h], h))
    best = list(row)
    if not _shape_ok(k, hud, best, mx, r_ideal, band):
        return None
    best_score = _score(k, hud, best, mx)
    deltas = (-0.3, -0.2, -0.1, 0.1, 0.2, 0.3)
    for _ in range(10_000):
        improved = False
        for h in order:
            for d in deltas:
                trial = list(best)
                trial[h] = round(trial[h] + d, 1)
                if trial[h] <= 0:
                    continue
                if not _shape_ok(k, hud, trial, mx, r_ideal, band):
                    continue
                s = _score(k, hud, trial, mx)
                if s < best_score:
                    best, best_score, improved = trial, s, True
        if not improved:
            break
    return best if _legal(k, hud, best, mx) else None


def generate_classic_row(
    k: int, hud: list[float] | None = None, mx: float | None = None
) -> list[float]:
    """One pick: lock max, solve the geometric ladder onto 0.9650.

    `mx` defaults to this module's `MAX_LADDER[k]`. Off `medium`/`high` pass
    their own max so they can reuse the same solver without mutating classic.
    """
    hud = hud or CLASSIC_HUD[k]
    mx = MAX_LADDER[k] if mx is None else mx
    seed, r_ideal = _seed_geometric(k, hud, mx)
    snapped = _snap(k, hud, seed, mx)
    for band in RATIO_BANDS:
        row = _repair(k, hud, snapped, mx, r_ideal, band)
        if row is not None:
            return row
    raise RuntimeError(f"pick_{k}: no legal progressive row under max {mx}")


def generate_classic_off() -> dict[int, list[float]]:
    return {k: generate_classic_row(k, hud) for k, hud in sorted(CLASSIC_HUD.items())}


#: Shipped Off `classic` chart (picks 2-10). Generated by the max-anchored
#: geometric ladder onto 0.9650. Pick 2 cannot hit 0.9650 exactly:
#: 1.7/5.4 = 0.965385 is the closest legal pair.
CLASSIC_OFF: dict[int, list[float]] = {
    2: [0.0, 1.7, 5.4],
    3: [0.0, 0.0, 5.5, 17.5],
    4: [0.0, 0.0, 2.6, 8.6, 30.0],
    5: [0.0, 0.0, 1.3, 4.9, 19.5, 75.0],
    6: [0.0, 0.0, 0.0, 3.9, 14.8, 54.2, 200.0],
    7: [0.0, 0.0, 0.0, 1.9, 8.2, 34.4, 144.2, 600.0],
    8: [0.0, 0.0, 0.0, 1.3, 4.9, 17.1, 60.1, 212.0, 750.0],
    9: [0.0, 0.0, 0.0, 1.0, 3.2, 9.5, 30.5, 92.7, 290.1, 900.0],
    10: [0.0, 0.0, 0.0, 0.8, 2.2, 6.3, 16.7, 47.7, 129.3, 360.7, 1000.0],
}

#: Geometric lock replaces the restair `shape_lock` for this chart.
SHAPE_LOCKED: frozenset[int] = frozenset(range(2, 11))


def _validate() -> None:
    generated = generate_classic_off()
    prev_max = 2.6  # classic pick_1 lattice max
    for k, row in sorted(CLASSIC_OFF.items()):
        hud = CLASSIC_HUD[k]
        assert row == generated[k], (
            f"pick_{k}: baked CLASSIC_OFF {row} != generator {generated[k]}"
        )
        assert len(row) == k + 1, f"pick_{k}: row length {len(row)} != {k + 1}"
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} is off the 0.1x lattice"
            )
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from the Classic HUD shape"
        )
        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: ladder is not strictly increasing: {row}"
        )
        expected_max = MAX_LADDER[k]
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != designed max {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed previous max {prev_max}"
        )
        prev_max = max(row)
        rtp = _exact_rtp(k, row)
        lo, hi = MODE_RTP_BAND
        assert lo < rtp < hi, f"pick_{k}: rtp {float(rtp):.6f} outside band"
        assert RTP_WINDOW[0] <= rtp <= RTP_WINDOW[1], (
            f"pick_{k}: rtp {float(rtp):.6f} outside designed window "
            f"{RTP_WINDOW[0]:.4f}-{RTP_WINDOW[1]:.4f}"
        )
        stats = base_stats(k, row)
        assert stats["std"] >= STD_MIN, (
            f"pick_{k}: std {stats['std']:.3f} < {STD_MIN} (Base Mode STD floor)"
        )
        assert stats["hit_rate"] >= 0.021, f"pick_{k}: hit rate below 1 in 50"
        assert stats["etl_sum"] <= 1.45, f"pick_{k}: etl_sum over the 3-Star gate"


_validate()


def classic_off_summary() -> str:
    lines = []
    for k, row in sorted(CLASSIC_OFF.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        rtp = float(_exact_rtp(k, row))
        stats = base_stats(k, row)
        pay = [m for m in row if m > 0]
        ratios = [b / a for a, b in zip(pay, pay[1:])]
        step = f"{min(ratios):.2f}-{max(ratios):.2f}" if ratios else "-"
        lines.append(
            f"classic_pick_{k:<2d} [{cells}] "
            f"rtp={rtp:.6f} edge={1 - rtp:.4%} "
            f"std={stats['std']:.3f} step=x{step} max={max(row):g}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(classic_off_summary())
