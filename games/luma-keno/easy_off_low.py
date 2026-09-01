"""Off `low` (Easy analogue) — Keno Xtreme Easy shape, retargeted to 96.5% RTP.

The competitor Easy HUD is ~99.0% RTP (pick 9 ~97.7%). Stake's page claim
for the blended game is 96.50% / 3.50% house edge. Off `low` copies the HUD
**zeros and maxes**, then spends leftover RTP on the body so each pick lands
as close as the 0.1x lattice allows to `RTP_TARGET` (0.9650).

Algorithm (per pick k)
----------------------
1. Lock m[k] = Easy max (pick 2 is 4.7, not 4.5: 1.8/4.5 is 0.952).
2. Keep the HUD zero prefix (same first paying hit).
3. leftover = 0.9650 - P(k) * max.
4. Split leftover in the same *shares* the HUD spent on body hits:
     share[h] = P(h) * HUD[h] / sum_body(P * HUD)
     m[h]     = leftover * share[h] / P(h)
5. Snap to the 0.1x lattice, then hill-climb body cells by 0.1x to minimise
   |RTP - 0.9650|. Illegal HUD cells (0.25 / 3.68 / 0.47 / 2.25) may only
   snap down. Body drift vs the floor-snapped HUD stays within +/-1.2.

pick_1 stays on the closed-form lattice in keno_pick_one.py (0.50 / 2.30
plus the advertised +0.1 miss bonus), which is already 0.9650.

Scope: **Off only.** Earn `low` and the buy chips keep their own ladders.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import (
    MODE_RTP_BAND,
    RTP_TARGET,
    STD_MIN,
    base_coeff,
    base_stats,
)

#: Designed window around 0.9650, inside MODE_RTP_BAND.
RTP_WINDOW = (0.9630, 0.9655)

#: Competitor Easy HUD rows. Shape + leftover-share template only.
EASY_HUD = {
    2: [0.00, 1.90, 4.50],
    3: [0.00, 1.00, 3.10, 10.40],
    4: [0.00, 0.80, 1.80, 5.00, 22.50],
    5: [0.00, 0.25, 1.40, 4.10, 16.50, 36.00],
    6: [0.00, 0.00, 1.00, 3.68, 7.00, 16.50, 40.00],
    7: [0.00, 0.00, 0.47, 3.00, 4.50, 14.00, 31.00, 60.00],
    8: [0.00, 0.00, 0.00, 2.20, 4.00, 13.00, 22.00, 55.00, 70.00],
    9: [0.00, 0.00, 0.00, 1.50, 3.00, 8.00, 15.00, 44.00, 60.00, 85.00],
    10: [0.00, 0.00, 0.00, 1.40, 2.25, 4.50, 8.00, 17.00, 50.00, 80.00, 100.00],
}

GRID = Fraction("0.1")
_TARGET = Fraction(str(RTP_TARGET))
_MAX_DRIFT = 1.2


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(
        Fraction(str(c)) * Fraction(str(m)) for c, m in zip(base_coeff(k), row)
    )


def _floor_snap(hud: list[float]) -> list[float]:
    return [float(Fraction((Fraction(str(m)) * 10).__floor__(), 10)) for m in hud]


def locked_max(k: int, hud: list[float]) -> float:
    """Easy max, except pick 2 where 4.5 cannot reach the 0.965 band."""
    return 4.7 if k == 2 else float(max(hud))


def _snap(value: Fraction) -> float:
    if value <= 0:
        return 0.0
    ticks = int(value / GRID + Fraction("1/2"))
    return float(ticks * GRID)


def _legal(k: int, hud: list[float], row: list[float], mx: float) -> bool:
    if len(row) != k + 1:
        return False
    if any(abs(m * 10 - round(m * 10)) > 1e-9 for m in row if m):
        return False
    if [m == 0 for m in row] != [m == 0 for m in hud]:
        return False
    paying = [m for m in row if m > 0]
    if not all(b > a for a, b in zip(paying, paying[1:])):
        return False
    if max(row) != mx:
        return False
    snapped = _floor_snap(hud)
    for h, (m, s) in enumerate(zip(row, snapped)):
        if abs(m - s) > _MAX_DRIFT + 1e-9:
            return False
        if hud[h] != s and m > s + 1e-9:
            return False
    rtp = _exact_rtp(k, row)
    lo, hi = MODE_RTP_BAND
    if not (lo < float(rtp) < hi):
        return False
    if not (RTP_WINDOW[0] <= float(rtp) <= RTP_WINDOW[1]):
        return False
    stats = base_stats(k, row)
    if stats["std"] < STD_MIN:
        return False
    if stats["hit_rate"] < 0.021:
        return False
    if stats["etl_sum"] > 1.45:
        return False
    return True


def _score(k: int, hud: list[float], row: list[float], mx: float) -> tuple:
    rtp = _exact_rtp(k, row)
    drift = sum(abs(a - b) for a, b in zip(row, hud))
    legal = 0 if _legal(k, hud, row, mx) else 1
    return (legal, abs(rtp - _TARGET), drift)


def _seed_from_shares(k: int, hud: list[float], mx: float) -> list[float]:
    """Scale the HUD's leftover-RTP shares onto 0.9650 - P(k)*max."""
    probs = [Fraction(str(c)) for c in base_coeff(k)]
    hud_f = [Fraction(str(m)) for m in hud]
    leftover_hud = sum(probs[h] * hud_f[h] for h in range(k))
    leftover = _TARGET - probs[k] * Fraction(str(mx))
    row = [0.0] * (k + 1)
    row[k] = mx
    if leftover_hud <= 0 or leftover <= 0:
        return row
    for h in range(k):
        if hud[h] == 0 or probs[h] == 0:
            continue
        share = (probs[h] * hud_f[h]) / leftover_hud
        row[h] = _snap(leftover * share / probs[h])
    for h in range(k):
        if hud[h] == 0:
            row[h] = 0.0
    paying = [h for h in range(k + 1) if hud[h] > 0]
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + 0.1, 1)
        if b == k and row[a] >= mx:
            row[a] = round(mx - 0.1, 1)
    return row


def _seed_trim_hud(k: int, hud: list[float], mx: float) -> list[float]:
    """Floor-snap the HUD, lock the max, then cut the fattest body cell
    until RTP sits inside MODE_RTP_BAND. Easy is ~99%, so this is the
    usual way onto the 0.965 fleet."""
    row = _floor_snap(hud)
    row[k] = mx
    for h in range(k):
        if hud[h] == 0:
            row[h] = 0.0
    body = [h for h in range(k) if hud[h] > 0]
    lo, hi = MODE_RTP_BAND
    for _ in range(200):
        rtp = float(_exact_rtp(k, row))
        if lo < rtp < hi and _legal(k, hud, row, mx):
            return row
        if rtp <= lo:
            break
        # Drop the body cell that spends the most RTP, keeping the ladder.
        best_h = None
        best_coin = -1.0
        for h in body:
            floor_h = 0.1 if h == body[0] else round(row[h - 1] + 0.1, 1)
            if h > 0 and hud[h - 1] == 0:
                floor_h = 0.1
            if row[h] - 0.1 < floor_h - 1e-9:
                continue
            coin = float(base_coeff(k)[h]) * 0.1
            if coin > best_coin:
                best_h, best_coin = h, coin
        if best_h is None:
            break
        row[best_h] = round(row[best_h] - 0.1, 1)
    return row


def _shape_ok(k: int, hud: list[float], row: list[float], mx: float) -> bool:
    """Lattice / zeros / max / drift — RTP and rating gates are scored, not
    required, so the climb can walk an ~99% HUD seed into the 0.965 band."""
    if len(row) != k + 1 or max(row) != mx:
        return False
    if any(abs(m * 10 - round(m * 10)) > 1e-9 for m in row if m):
        return False
    if [m == 0 for m in row] != [m == 0 for m in hud]:
        return False
    paying = [m for m in row if m > 0]
    if not all(b > a for a, b in zip(paying, paying[1:])):
        return False
    snapped = _floor_snap(hud)
    for h, (m, s) in enumerate(zip(row, snapped)):
        if abs(m - s) > _MAX_DRIFT + 1e-9:
            return False
        if hud[h] != s and m > s + 1e-9:
            return False
    return True


def _neighbours(row: list[float], body: list[int]) -> list[list[float]]:
    """Single-cell 0.1x nudges and leftover transfers between two body cells."""
    out: list[list[float]] = []
    for h in body:
        for delta in (-0.3, -0.2, -0.1, 0.1, 0.2, 0.3):
            trial = list(row)
            trial[h] = round(trial[h] + delta, 1)
            if trial[h] > 0:
                out.append(trial)
    for src in body:
        for dst in body:
            if src == dst:
                continue
            for steps in (1, 2, 3, 4):
                trial = list(row)
                trial[src] = round(trial[src] - 0.1 * steps, 1)
                trial[dst] = round(trial[dst] + 0.1 * steps, 1)
                if trial[src] > 0:
                    out.append(trial)
    return out


def _climb(k: int, hud: list[float], start: list[float], mx: float) -> list[float] | None:
    body = [h for h in range(k) if hud[h] > 0]
    best = list(start)
    if not _shape_ok(k, hud, best, mx):
        return None
    best_score = _score(k, hud, best, mx)
    improved = True
    while improved:
        improved = False
        for trial in _neighbours(best, body):
            if not _shape_ok(k, hud, trial, mx):
                continue
            score = _score(k, hud, trial, mx)
            if score < best_score:
                best, best_score, improved = trial, score, True
    return best if _legal(k, hud, best, mx) else None


def retarget_easy_row(k: int, hud: list[float]) -> list[float]:
    """One pick: lock the Easy max, spend leftover RTP on the HUD body shape."""
    mx = locked_max(k, hud)
    snapped = _floor_snap(hud)
    snapped[k] = mx
    seeds = [
        _seed_from_shares(k, hud, mx),
        _seed_trim_hud(k, hud, mx),
        snapped,
    ]
    if k in EASY_OFF_LOW:
        seeds.append(list(EASY_OFF_LOW[k]))
    best: list[float] | None = None
    best_score = None
    for seed in seeds:
        climbed = _climb(k, hud, seed, mx)
        if climbed is None:
            continue
        score = _score(k, hud, climbed, mx)
        if best_score is None or score < best_score:
            best, best_score = climbed, score
    if best is None:
        raise RuntimeError(f"pick_{k}: no legal 0.9650 row under the Easy lock")
    return best


def generate_easy_off_low() -> dict[int, list[float]]:
    return {k: retarget_easy_row(k, hud) for k, hud in sorted(EASY_HUD.items())}


#: Shipped Off `low` chart (picks 2-10). Generated by leftover-RTP fill of
#: EASY_HUD onto 0.9650, then hill-climb + body transfers on the 0.1x lattice.
#: Pick 2 cannot hit 0.9650: 1.8/4.7 = 0.9635 is the closest legal pair
#: (1.8/4.8 is 0.9692, over the 0.967 ceiling).
EASY_OFF_LOW: dict[int, list[float]] = {
    2: [0.0, 1.8, 4.7],
    3: [0.0, 0.6, 4.2, 10.4],
    4: [0.0, 0.8, 1.7, 4.9, 22.5],
    5: [0.0, 0.2, 1.4, 4.1, 16.1, 36.0],
    6: [0.0, 0.0, 1.0, 3.6, 6.4, 16.4, 40.0],
    7: [0.0, 0.0, 0.4, 3.0, 4.4, 14.7, 30.2, 60.0],
    8: [0.0, 0.0, 0.0, 2.1, 4.0, 12.8, 21.7, 55.5, 70.0],
    9: [0.0, 0.0, 0.0, 1.5, 2.9, 8.0, 14.7, 44.8, 60.6, 85.0],
    10: [0.0, 0.0, 0.0, 1.4, 2.1, 4.4, 8.1, 17.4, 50.8, 81.2, 100.0],
}


def _validate() -> None:
    prev_max = 0.0
    for k, row in sorted(EASY_OFF_LOW.items()):
        hud = EASY_HUD[k]
        assert len(row) == k + 1, f"pick_{k}: row length {len(row)} != {k + 1}"
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} is off the 0.1x lattice"
            )
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from the Easy HUD shape"
        )
        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: ladder is not strictly increasing: {row}"
        )
        expected_max = locked_max(k, hud)
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != designed max {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed pick_{k - 1} max {prev_max}"
        )
        prev_max = max(row)
        snapped = _floor_snap(hud)
        for h, (m, s) in enumerate(zip(row, snapped)):
            assert -_MAX_DRIFT - 1e-9 <= m - s <= _MAX_DRIFT + 1e-9, (
                f"pick_{k} h={h}: {s} -> {m} moves more than +/-{_MAX_DRIFT}"
            )
            if hud[h] != s:
                assert m <= s + 1e-9, (
                    f"pick_{k} h={h}: illegal HUD cell {hud[h]} snapped UP to {m}"
                )
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


def easy_low_summary() -> str:
    lines = []
    for k, row in sorted(EASY_OFF_LOW.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        rtp = float(_exact_rtp(k, row))
        lines.append(
            f"low_pick_{k:<2d} [{cells}] rtp={rtp:.6f} edge={1 - rtp:.4%}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_low_summary())
