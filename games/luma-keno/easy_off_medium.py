"""Off `medium` (Keno Xtreme Medium / Crazy analogue) paytable — HUD copy.

Source: wiki/sources/keno-xtreme-medium-hud.md (screenshots 2026-09-01).
Competitor Medium RTP is well under the fleet window, so the copy RAISES
body cells into [0.9630, 0.9655]. Illegal HUD cells (0.95 / 1.75) snap DOWN
onto the 0.1x grid. There is no Easy ±1.2 drift cap.

HUD pick 3 max 75x overshoots RTP and 2-Star ETL40; luma-keno must not copy
it. Highest in-window max is 60.3x.

Pick 2: HUD 9.00 cannot land on-grid (1.1/9.0 = 0.9423 under; 1.1/9.4 =
0.965385). Same lattice exception as Classic 5.0→5.4.

Jackpot-shaped HUD cells (>=9x on picks 8-10, >=40x otherwise) stay put.
pick_1 stays lattice [0.2, 3.2] in keno_pick_one.py.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import MODE_RTP_BAND, STD_MIN, base_coeff, base_stats

RTP_WINDOW = (0.9630, 0.9655)

MEDIUM_HUD = {
    2: [0.00, 0.95, 9.00],
    3: [0.00, 0.00, 1.75, 75.00],
    4: [0.00, 0.00, 0.95, 7.00, 175.0],
    5: [0.00, 0.00, 1.20, 3.00, 9.00, 450.0],
    6: [0.00, 0.00, 0.00, 1.50, 5.00, 50.00, 650.0],
    7: [0.00, 0.00, 0.00, 0.95, 3.00, 7.50, 90.00, 750.0],
    8: [0.00, 0.00, 0.00, 0.95, 2.00, 5.00, 15.00, 150.0, 2500.0],
    9: [0.00, 0.00, 0.00, 0.95, 1.10, 2.50, 5.00, 40.00, 350.0, 4000.0],
    10: [0.00, 0.00, 0.00, 0.50, 0.95, 1.50, 3.00, 9.00, 40.00, 400.0, 5000.0],
}

MEDIUM_OFF: dict[int, list[float]] = {
    2: [0.0, 1.1, 9.4],
    3: [0.0, 0.0, 1.7, 60.3],
    4: [0.0, 0.0, 1.3, 7.2, 175.0],
    5: [0.0, 0.0, 1.6, 3.3, 9.0, 450.0],
    6: [0.0, 0.0, 0.0, 4.9, 8.8, 50.0, 650.0],
    7: [0.0, 0.0, 0.0, 2.9, 7.4, 13.6, 90.0, 750.0],
    8: [0.0, 0.0, 0.0, 1.9, 4.9, 11.2, 15.0, 150.0, 2500.0],
    9: [0.0, 0.0, 0.0, 1.4, 3.2, 7.9, 13.0, 40.0, 350.0, 4000.0],
    10: [0.0, 0.0, 0.0, 0.7, 2.6, 7.4, 8.9, 9.0, 40.0, 400.0, 5000.0],
}


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(coeff * Fraction(str(m)) for coeff, m in zip(base_coeff(k), row))


def _validate() -> None:
    prev_max = 3.2
    for k, row in sorted(MEDIUM_OFF.items()):
        hud = MEDIUM_HUD[k]
        assert len(row) == k + 1
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} off 0.1x"
            )
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from Medium HUD"
        )
        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: not strictly increasing: {row}"
        )
        expected_max = {2: 9.4, 3: 60.3}.get(k, max(hud))
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed {prev_max}"
        )
        body_top = max(row[h] for h in range(k) if row[h] > 0)
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


_validate()


def medium_off_summary() -> str:
    lines = []
    for k, row in sorted(MEDIUM_OFF.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        lines.append(
            f"medium_pick_{k:<2d} [{cells}] rtp={float(_exact_rtp(k, row)):.6f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(medium_off_summary())
