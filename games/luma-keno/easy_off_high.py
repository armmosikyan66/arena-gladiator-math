"""Off `high` (Keno Xtreme Hard / Degen analogue) paytable — HUD copy.

Source: /workspace/keno-xtreme-hard.md (screenshots 2026-09-01).
Competitor Hard RTP is player-favor on picks 2-6 (pick 3 at 500x is ~614%),
so the copy RAISES body cells into [0.9630, 0.9655] and cuts a max only when
that window / etl40 0.88 / cvar 700 forbids it. Illegal HUD cells (0.25)
snap DOWN onto the 0.1x grid. There is no Easy ±1.2 drift cap.

HUD pick 3 max 500x overshoots RTP and etl40; luma-keno must not copy it.
Highest in-window max is 71.6x (same class as Medium 75→60.3).

Pick 2: HUD 20.00 with a two-zero prefix cannot land in-window (20*P(2) =
1.1538). Lattice exception: keep zeros, cut max to 16.7 (16.7*P(2) = 0.96346).

Pick 10 KEEP 50000 — RTP/etl40/cvar all allow it. MAX_PAYOUT_ABS 100000 is
the settled ceiling; do not cut Off to help Earn (50000 x Lumen x2 x Pulse x2
= 200000 vs the 100k cap is an Earn problem).

Jackpot-shaped HUD cells stay put. Pick 8 keeps 40x; remainder packs onto
0.50→2.9 and 1.50→39.6 (same class as Medium 5.00→11.2 under a frozen 15).

pick_1 stays lattice pick_one_row("high") = [0.1, 3.5]; do not force HUD 4.00.

Pick 9 restair (shape lock)
---------------------------
The row was 0.2 / 0.4 / 28.4 / 39.9 / 40 / 3500 / 40000. Hits 6, 7 and 8 read
28.4 / 39.9 / 40 - the HUD cannot separate the last two at all - with a 71x
wall under them and an 87x cliff above. It now climbs
0.2 / 1 / 16 / 92 / 500 / 3000 / 40000 (rtp 0.964248): a 16x wall off the 1x
consolation, then 5.75x / 5.43x / 6x through the body and 13.33x on the final
catch. Jackpot holds 40000; only the body moved.

Picks 6 and 8 are NOT restaired, and cannot be at their current maxes. Off high
6 needs its 3484.6 ETL cut lowered to about 1869x before any lock-clean ladder
reaches the RTP window, and pick 8 needs 25000 down to about 24870 - and even
there the only clean ladder is the one at maximum ratio everywhere, so it has
no shaping room. Both are top decisions, not solver settings. See
`shape_feasibility.py`.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import MODE_RTP_BAND, STD_MIN, base_coeff, base_stats
from shape_lock import assert_shape, ratios_of

RTP_WINDOW = (0.9630, 0.9655)

HIGH_HUD = {
    2: [0, 0, 20.00],
    3: [0, 0, 0.50, 500],
    4: [0, 0, 0, 1.50, 1000],
    5: [0, 0, 0, 0.50, 25.00, 2500],
    6: [0, 0, 0, 0.25, 1.50, 350.0, 6000],  # 0.25 snaps DOWN to 0.2
    7: [0, 0, 0, 0.10, 0.50, 3.00, 950.0, 12500],
    8: [0, 0, 0, 0.10, 0.50, 1.50, 40.00, 1500, 25000],
    9: [0, 0, 0, 0.10, 0.30, 0.50, 5.00, 40.00, 3500, 40000],
    10: [0, 0, 0, 0.10, 0.30, 0.50, 1.50, 3.00, 90.00, 4500, 50000],
}

HIGH_OFF: dict[int, list[float]] = {
    2: [0.0, 0.0, 16.7],
    3: [0.0, 0.0, 0.7, 71.6],
    4: [0.0, 0.0, 0.0, 2.2, 382.4],
    5: [0.0, 0.0, 0.0, 0.5, 25.0, 1792.4],
    6: [0.0, 0.0, 0.0, 3.0, 10.0, 79.0, 3484.6],  # restaired; was 0.3/1.9/350 (184x body cliff)
    7: [0.0, 0.0, 0.0, 0.4, 2.9, 61.3, 950.0, 12500.0],
    8: [0.0, 0.0, 0.0, 0.4, 2.9, 39.6, 40.0, 1500.0, 25000.0],
    9: [0.0, 0.0, 0.0, 0.2, 1.0, 16.0, 92.0, 500.0, 3000.0, 40000.0],
    10: [0.0, 0.0, 0.0, 0.2, 0.4, 4.3, 78.5, 200.0, 700.0, 4500.0, 50000.0],  # industry stair (not HUD 1.5/3/90 pack)
}

# HUD max kept unless RTP / etl40 / cvar forced a cut.
CUT_MAX = {2: 16.7, 3: 71.6, 4: 382.4, 5: 1792.4, 6: 3484.6}

#: Picks restaired under `shape_lock`. Pick 10 predates the lock and does not
#: satisfy it (0.2 -> 0.4 is 2x on a pair that reads as two wins, and 4.3 -> 78.5
#: is an 18.3x wall in the body), but it is certified and must not regress, so it
#: is graded by the legacy assertions only.
#:
#: Pick 6 keeps the 3484.6 etl cap, so its final catch is 44x and the 8-15x
#: last-catch band cannot apply; the short-pick scope grades that step as a top
#: rather than a body pair. What the restair fixes is the body: 1.9 -> 350 was
#: a 184x cliff between two paying cells, now 3 / 10 / 79 steps 3.33x then 7.9x.
#: Hit rate is unchanged at 15.28% because the paying hits did not move.
SHAPE_LOCKED = frozenset({6, 9})


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(coeff * Fraction(str(m)) for coeff, m in zip(base_coeff(k), row))


def _validate() -> None:
    prev_max = 3.5
    for k, row in sorted(HIGH_OFF.items()):
        hud = HIGH_HUD[k]
        assert len(row) == k + 1
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} off 0.1x"
            )
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from High HUD"
        )
        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: not strictly increasing: {row}"
        )
        expected_max = CUT_MAX.get(k, float(max(hud)))
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed {prev_max}"
        )
        body_vals = [row[h] for h in range(k) if row[h] > 0]
        if body_vals:
            body_top = max(body_vals)
            assert body_top <= expected_max - 0.1 + 1e-9, (
                f"pick_{k}: body {body_top} flattens into max {expected_max}"
            )
        prev_max = max(row)
        rtp = _exact_rtp(k, row)
        lo, hi = MODE_RTP_BAND
        assert lo < rtp < hi, f"pick_{k}: rtp {float(rtp):.6f} outside band"
        assert RTP_WINDOW[0] <= rtp <= RTP_WINDOW[1], (
            f"pick_{k}: rtp {float(rtp):.6f} outside {RTP_WINDOW}"
        )
        stats = base_stats(k, row)
        assert stats["std"] >= STD_MIN, f"pick_{k}: std {stats['std']:.3f}"
        assert stats["hit_rate"] >= 0.021, f"pick_{k}: hit rate"
        assert stats["etl_sum"] <= 1.45, f"pick_{k}: etl_sum {stats['etl_sum']:.3f}"
        assert stats["etl40"] <= 0.88, f"pick_{k}: etl40 {stats['etl40']:.3f}"
        assert stats["cvar"] <= 700.0, f"pick_{k}: cvar {stats['cvar']:.1f}"
        if k in SHAPE_LOCKED:
            # Every paying pair visibly apart, >=2.5x across the body, <=8x
            # outside the final catch, and a final catch inside 8-15x. This is
            # what stops leftover RTP being packed onto neighbouring cells.
            assert_shape(row, k, label=f"high_pick_{k}")


_validate()


def high_off_summary() -> str:
    lines = []
    for k, row in sorted(HIGH_OFF.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        lines.append(
            f"high_pick_{k:<2d} [{cells}] rtp={float(_exact_rtp(k, row)):.6f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(high_off_summary())
