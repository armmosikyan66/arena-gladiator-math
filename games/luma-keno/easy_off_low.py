"""Off `low` (Easy analogue) paytable — Keno Xtreme Easy HUD copy.

Source: wiki/sources/keno-xtreme-easy-hud.md (screenshots 2026-08-31).
The competitor table is ~99.0% RTP and carries five cells that are illegal
on the Stake Engine 0.1x lattice (0.65 / 0.25 / 3.68 / 0.47 / 2.25), so it
cannot be pasted. Per the copy rule (skill `keno-math`, Low):

  1. keep the shape — same zero prefix, same first paying hit;
  2. keep the maxes (Easy tops stay modest: 100x on pick_10, not 400x);
  3. snap illegal cells DOWN onto the 0.1x grid;
  4. trim the smallest number of body cells so exact RTP lands in the
     designed window [0.9630, 0.9655] inside MODE_RTP_BAND.

Picks 2 / 7 / 10 are the snaps already published in the wiki and the skill;
picks 3-6 / 8 / 9 are derived here under the same rules (search ranked by:
keep max > in window > fewest moved cells > least total drift > closest to
0.9645). Every ladder strictly increases, and the per-pick maxes strictly
increase across picks:

    2.3 (pick_1) < 4.7 < 10.4 < 22.5 < 36 < 40 < 60 < 70 < 85 < 100

Scope: **Off only.** Earn `low` and the buy chips keep their own ladders
(Earn low pick_8-10 advertise 100x so Lumen x2 x Pulse x2 settles 400x).
pick_1 stays on the closed-form lattice in keno_pick_one.py.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import MODE_RTP_BAND, STD_MIN, base_coeff, base_stats

#: Designed RTP window. Inside MODE_RTP_BAND with margin on both sides so
#: the fleet Cross-Mode spread (0.50pp over all 160 modes) never binds here.
RTP_WINDOW = (0.9630, 0.9655)

#: Competitor Easy HUD rows, for provenance and shape checks only.
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

#: The shipped Off `low` chart (picks 2-10). Illegal HUD cells are floored
#: to the 0.1x grid; body cells are trimmed just enough to reach the window.
EASY_OFF_LOW: dict[int, list[float]] = {
    2: [0.0, 1.8, 4.7],
    3: [0.0, 0.6, 4.2, 10.4],
    4: [0.0, 0.8, 1.7, 4.9, 22.5],
    5: [0.0, 0.2, 1.4, 4.1, 16.1, 36.0],
    6: [0.0, 0.0, 1.0, 3.6, 6.4, 16.5, 40.0],
    7: [0.0, 0.0, 0.4, 3.0, 4.4, 14.4, 31.0, 60.0],
    8: [0.0, 0.0, 0.0, 2.1, 4.0, 12.8, 22.0, 55.0, 70.0],
    9: [0.0, 0.0, 0.0, 1.5, 3.0, 7.5, 15.0, 44.0, 60.0, 85.0],
    10: [0.0, 0.0, 0.0, 1.4, 2.1, 4.4, 8.0, 17.0, 50.0, 80.0, 100.0],
}


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(
        coeff * Fraction(str(m)) for coeff, m in zip(base_coeff(k), row)
    )


def _validate() -> None:
    prev_max = 0.0
    for k, row in sorted(EASY_OFF_LOW.items()):
        hud = EASY_HUD[k]
        assert len(row) == k + 1, f"pick_{k}: row length {len(row)} != {k + 1}"

        # 0.1x grid: LUT payout = int(round(m * 100)) must be a multiple of 10.
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} is off the 0.1x lattice"
            )

        # Shape: same zero prefix as the HUD (same first paying hit).
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from the Easy HUD shape"
        )

        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: ladder is not strictly increasing: {row}"
        )

        # Maxes copied from the HUD (pick_2 excepted: the published snap moves
        # 4.5 -> 4.7 because 1.8/4.5 lands at 0.952, under the band), strictly
        # increasing across picks.
        expected_max = 4.7 if k == 2 else max(hud)
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != designed max {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed pick_{k - 1} max {prev_max}"
        )
        prev_max = max(row)

        # Cell deltas vs the floor-snapped HUD stay small and legal-only-down.
        snapped = [float(Fraction((Fraction(str(m)) * 10).__floor__(), 10)) for m in hud]
        for h, (m, s) in enumerate(zip(row, snapped)):
            assert -1.2 - 1e-9 <= m - s <= 1.2 + 1e-9, (
                f"pick_{k} h={h}: {s} -> {m} moves more than +/-1.2"
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

        # Grade through the same stats path check_gates uses.
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
        lines.append(f"low_pick_{k:<2d} [{cells}] rtp={float(_exact_rtp(k, row)):.6f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(easy_low_summary())
