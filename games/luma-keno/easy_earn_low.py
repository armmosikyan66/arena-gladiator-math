"""Earn `low` (Easy analogue) — HUD zeros + leftover-share, Lumen/Pulse priced in.

Off `low` is the Easy HUD leftover-filled onto 96.5% with plain hypergeometric
weights (`easy_off_low.py`). Earn prices Lumen ×2 and Pulse ×2 into the same
identity, so the *advertised* row must be cheaper: settled How-to is
advertised ×4.

Algorithm (per pick k ≥ 2)
--------------------------
1. Keep the Easy HUD zero prefix (same first paying hit as Off `low`).
2. Lock m[k] = designed max. Picks 5–7 pin the Off max. Picks 8–10 advertise
   100× so a full card settles 400× (Easy ceiling). Picks 2–4 snap to the
   nearest 0.1× above Off that can land inside the designed RTP window —
   Off 4.7 / 10.4 / 22.5 have no in-window Earn-coeff pair.
3. leftover = 0.9650 − coeff[k] · max, with `effective_coeff` over the HUD
   paying set (extras only open on a paying main ten).
4. Split leftover in the same *shares* the HUD spent on body hits, using
   Earn coefficients not P(h):
     share[h] = coeff[h] · HUD[h] / sum_body(coeff · HUD)
     m[h]     = leftover · share[h] / coeff[h]
5. Snap to the 0.1× lattice, then hill-climb body cells by 0.1× to minimise
   |RTP − 0.9650|.

pick_1 stays on the closed-form lattice in keno_pick_one.py ([0.5, 2.1] →
0.9630). Not in EASY_EARN_LOW.

Scope: **Earn only.** Off `low` and the buy chips keep their own ladders.

Deep picks 8–10 cannot host a shape-lock restair at 100× (reachable RTP
ceiling ~0.45 with 6–8 paying cells). That is the Easy identity — frequent
small pays, modest jackpot — not a packing bug. Leave those rows on
leftover-share; do not raise Easy's 70/85/100 toward classic 1000×.
"""

from __future__ import annotations

from fractions import Fraction

from easy_off_low import EASY_HUD, locked_max
from keno_pick_one import (
    MODE_RTP_BAND,
    RTP_TARGET,
    STD_MIN,
    effective_coeff,
    settled_stats,
)

#: Designed window around 0.9650, inside MODE_RTP_BAND.
RTP_WINDOW = (0.9630, 0.9655)

GRID = Fraction("0.1")
_TARGET = Fraction(str(RTP_TARGET))
SETTLE = 4.0  # Lumen ×2 × Pulse ×2

#: Advertised max ladder. How-to = advertised × SETTLE must sit at or above
#: Off. Picks 8–10 flatten at the Easy pick-10 ceiling so a full card settles
#: 400× rather than three different How-tos.
MAX_LADDER = {
    2: 5.3,    # Off 4.7: no in-window Earn pair (1.4/4.7 = 0.960, 1.5/4.7 = 1.003)
    3: 10.9,   # Off 10.4: closest body is 0.9657, over the designed window
    4: 22.7,   # Off 22.5 packed 0.9/1.0/1.4; 22.7 is lock-clean
    5: 36.0,
    6: 40.0,
    7: 60.0,
    8: 100.0,
    9: 100.0,
    10: 100.0,
}


def _paying(hud: list[float]) -> list[int]:
    return [h for h, m in enumerate(hud) if m > 0]


def _coeff(k: int, hud: list[float]) -> tuple[float, ...]:
    return effective_coeff("low", k, frozenset(_paying(hud)))


def _exact_rtp(coeff: tuple[float, ...] | list[float], row: list[float]) -> Fraction:
    return sum(
        Fraction(str(c)) * Fraction(str(m)) for c, m in zip(coeff, row)
    )


def _snap(value: Fraction) -> float:
    if value <= 0:
        return 0.0
    ticks = int(value / GRID + Fraction("1/2"))
    return float(ticks * GRID)


def _shape_ok(k: int, hud: list[float], row: list[float], mx: float) -> bool:
    if len(row) != k + 1 or abs(max(row) - mx) > 1e-9:
        return False
    if any(abs(m * 10 - round(m * 10)) > 1e-9 for m in row if m):
        return False
    if [m == 0 for m in row] != [m == 0 for m in hud]:
        return False
    paying = [m for m in row if m > 0]
    return all(b > a for a, b in zip(paying, paying[1:]))


def _legal(k: int, hud: list[float], row: list[float], mx: float) -> bool:
    if not _shape_ok(k, hud, row, mx):
        return False
    coeff = _coeff(k, hud)
    rtp = float(_exact_rtp(coeff, row))
    lo, hi = MODE_RTP_BAND
    if not (lo < rtp < hi):
        return False
    if not (RTP_WINDOW[0] <= rtp <= RTP_WINDOW[1]):
        return False
    stats = settled_stats("low", k, row)
    if stats["std"] < STD_MIN:
        return False
    if stats["hit_rate"] < 0.021:
        return False
    if stats["etl_sum"] > 1.45:
        return False
    off_top = locked_max(k, hud)
    if stats["max_m"] + 1e-9 < off_top:
        return False
    return True


def _score(k: int, hud: list[float], row: list[float], mx: float) -> tuple:
    coeff = _coeff(k, hud)
    rtp = _exact_rtp(coeff, row)
    drift = sum(abs(a - b) for a, b in zip(row, hud))
    legal = 0 if _legal(k, hud, row, mx) else 1
    return (legal, abs(rtp - _TARGET), drift)


def _seed_from_shares(k: int, hud: list[float], mx: float) -> list[float]:
    coeff = [Fraction(str(c)) for c in _coeff(k, hud)]
    hud_f = [Fraction(str(m)) for m in hud]
    leftover_hud = sum(coeff[h] * hud_f[h] for h in range(k))
    leftover = _TARGET - coeff[k] * Fraction(str(mx))
    row = [0.0] * (k + 1)
    row[k] = mx
    if leftover_hud <= 0 or leftover <= 0:
        return row
    for h in range(k):
        if hud[h] == 0 or coeff[h] == 0:
            continue
        share = (coeff[h] * hud_f[h]) / leftover_hud
        row[h] = _snap(leftover * share / coeff[h])
    for h in range(k):
        if hud[h] == 0:
            row[h] = 0.0
    paying = _paying(hud)
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + 0.1, 1)
        if b == k and row[a] >= mx:
            row[a] = round(mx - 0.1, 1)
    return row


def _seed_scale_hud(k: int, hud: list[float], mx: float) -> list[float]:
    """Uniform scale of the HUD body onto leftover, then lock the max."""
    coeff = _coeff(k, hud)
    body_rtp = sum(coeff[h] * hud[h] for h in range(k) if hud[h] > 0)
    leftover = float(_TARGET) - coeff[k] * mx
    scale = leftover / body_rtp if body_rtp > 0 else 1.0
    row = [0.0] * (k + 1)
    for h in range(k):
        if hud[h] > 0:
            row[h] = _snap(Fraction(str(hud[h] * scale)))
    row[k] = mx
    paying = _paying(hud)
    for a, b in zip(paying, paying[1:]):
        if b != k and row[b] <= row[a]:
            row[b] = round(row[a] + 0.1, 1)
        if b == k and row[a] >= mx:
            row[a] = round(mx - 0.1, 1)
    return row


def _neighbours(row: list[float], body: list[int]) -> list[list[float]]:
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


def retarget_easy_earn_row(k: int, hud: list[float]) -> list[float]:
    mx = MAX_LADDER[k]
    seeds = [
        _seed_from_shares(k, hud, mx),
        _seed_scale_hud(k, hud, mx),
    ]
    if k in EASY_EARN_LOW:
        seeds.append(list(EASY_EARN_LOW[k]))
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
        raise RuntimeError(
            f"pick_{k}: no legal 0.9650 Earn row under advertised max {mx}"
        )
    return best


def generate_easy_earn_low() -> dict[int, list[float]]:
    return {k: retarget_easy_earn_row(k, hud) for k, hud in sorted(EASY_HUD.items())}


#: Shipped Earn `low` chart (picks 2-10). Leftover-RTP fill of EASY_HUD onto
#: 0.9650 with Earn coefficients (Lumen ×2 × Pulse ×2 priced in).
EASY_EARN_LOW: dict[int, list[float]] = {
    2: [0.0, 1.3, 5.3],
    3: [0.0, 0.7, 2.2, 10.9],
    4: [0.0, 0.5, 1.2, 3.4, 22.7],
    5: [0.0, 0.2, 0.9, 2.2, 10.0, 36.0],
    6: [0.0, 0.0, 0.6, 2.3, 4.2, 10.0, 40.0],
    7: [0.0, 0.0, 0.3, 1.6, 2.7, 7.9, 17.9, 60.0],
    8: [0.0, 0.0, 0.0, 1.2, 2.1, 7.0, 11.6, 29.4, 100.0],
    9: [0.0, 0.0, 0.0, 0.8, 1.5, 4.1, 8.1, 22.5, 31.3, 100.0],
    10: [0.0, 0.0, 0.0, 0.7, 1.3, 2.3, 4.3, 9.3, 26.7, 43.1, 100.0],
}


def _validate() -> None:
    generated = generate_easy_earn_low()
    prev_max = 2.1  # earn low pick_1 lattice max
    for k, row in sorted(EASY_EARN_LOW.items()):
        hud = EASY_HUD[k]
        mx = MAX_LADDER[k]
        assert row == generated[k], (
            f"pick_{k}: baked EASY_EARN_LOW {row} != generator {generated[k]}"
        )
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
        assert max(row) == mx, f"pick_{k}: max {max(row)} != designed max {mx}"
        assert max(row) >= prev_max, (
            f"pick_{k}: max {max(row)} below pick_{k - 1} max {prev_max}"
        )
        prev_max = max(row)
        off_top = locked_max(k, hud)
        stats = settled_stats("low", k, row)
        assert stats["max_m"] + 1e-9 >= off_top, (
            f"pick_{k}: How-to {stats['max_m']:.1f}x < Off {off_top:.1f}x"
        )
        rtp = float(_exact_rtp(_coeff(k, hud), row))
        lo, hi = MODE_RTP_BAND
        assert lo < rtp < hi, f"pick_{k}: rtp {rtp:.6f} outside band"
        assert RTP_WINDOW[0] <= rtp <= RTP_WINDOW[1], (
            f"pick_{k}: rtp {rtp:.6f} outside designed window "
            f"{RTP_WINDOW[0]:.4f}-{RTP_WINDOW[1]:.4f}"
        )
        assert abs(stats["rtp"] - rtp) < 1e-9, (
            f"pick_{k}: settled rtp {stats['rtp']:.6f} != coeff rtp {rtp:.6f}"
        )
        assert stats["std"] >= STD_MIN, (
            f"pick_{k}: std {stats['std']:.3f} < {STD_MIN} (Base Mode STD floor)"
        )
        assert stats["hit_rate"] >= 0.021, f"pick_{k}: hit rate below 1 in 50"
        assert stats["etl_sum"] <= 1.45, f"pick_{k}: etl_sum over the 3-Star gate"


_validate()


def easy_earn_low_summary() -> str:
    lines = []
    for k, row in sorted(EASY_EARN_LOW.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        stats = settled_stats("low", k, row)
        off_top = locked_max(k, EASY_HUD[k])
        lines.append(
            f"low_pick_{k:<2d}_earn [{cells}] "
            f"rtp={stats['rtp']:.6f} edge={1 - stats['rtp']:.4%} "
            f"std={stats['std']:.3f} hr={stats['hit_rate']:.4f} "
            f"how={stats['max_m']:.0f} off={off_top:g}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_earn_low_summary())
