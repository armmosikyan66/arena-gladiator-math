"""Off `classic` (Keno Xtreme Classic analogue) paytable — HUD copy.

Source: /workspace/keno-xtreme-classic-hud.md (screenshots 2026-09-01).
Competitor Classic HUD RTP is 42–91% (pick 7 is ~0.42), not ~99% like Easy,
so the copy RAISES body cells onto the designed window [0.9630, 0.9655]
inside MODE_RTP_BAND. There is no ±1.2 cell-drift cap — that Easy rule
would make Classic impossible.

Per the copy rule (skill `keno-math`, Classic):

  1. keep the shape — same zero prefix, same first paying hit;
  2. keep the HUD maxes, except pick 2 (see below);
  3. 0.1x lattice only;
  4. remainder-pack RTP onto mid-coeff body cells. Do not flatten the
     top of a ladder into the max (no 599.9/600 or 899.8/900 cliffs).
     HUD cells >= 40x (the jackpot ladder) stay put.

Pick 2 exception: on the 0.1x grid, max 5.0 with body 1.7 lands at
0.9423 and body 1.8 overshoots 0.9655. Same exception Easy used (4.5→4.7).
Search found [0.0, 1.7, 5.4] rtp=0.965385; no 5.0 on-grid solution exists.

Fill: greedy-raise highest-coeff body cells 0.1 at a time while
exact_rtp + coeff*0.1 <= 0.9655 and next_paying - 0.1 has room. If still
below 0.9630, pack remainder onto the next HUD body cell (lower coeff),
making room on a successor only when the HUD pair is already tight
(k=9/10 1.10/1.50/2.00). Do not raise 40/50/100/200/400/500/600/750/900/1000.

Picks 2-10 maxes strictly increase across picks:

    2.6 (pick_1) < 5.4 < 40 < 100 < 300 < 500 < 600 < 750 < 900 < 1000

Scope: **Off only.** Earn `classic` and the buy chips keep their own
ladders. pick_1 stays on the closed-form lattice in keno_pick_one.py
(classic miss 0.4, hit 2.6) and is not in CLASSIC_OFF.
"""

from __future__ import annotations

from fractions import Fraction

from keno_pick_one import MODE_RTP_BAND, STD_MIN, base_coeff, base_stats

#: Designed RTP window. Inside MODE_RTP_BAND with margin on both sides so
#: the fleet Cross-Mode spread (0.50pp over all 160 modes) never binds here.
RTP_WINDOW = (0.9630, 0.9655)

#: Competitor Classic HUD rows, for provenance and shape checks only.
#: All cells already on the 0.1x lattice.
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

#: The shipped Off `classic` chart (picks 2-10). Body cells are remainder-
#: packed just enough to reach the window; jackpot cells stay on the HUD.
CLASSIC_OFF: dict[int, list[float]] = {
    2: [0.0, 1.7, 5.4],
    3: [0.0, 0.0, 3.5, 40.0],
    4: [0.0, 0.0, 1.7, 9.4, 100.0],
    5: [0.0, 0.0, 1.5, 4.2, 10.3, 300.0],
    6: [0.0, 0.0, 0.0, 4.1, 9.2, 100.0, 500.0],
    7: [0.0, 0.0, 0.0, 2.9, 7.9, 9.0, 100.0, 600.0],
    8: [0.0, 0.0, 0.0, 2.5, 3.1, 9.0, 40.0, 200.0, 750.0],
    9: [0.0, 0.0, 0.0, 2.3, 2.4, 3.0, 5.0, 50.0, 400.0, 900.0],
    10: [0.0, 0.0, 0.0, 1.9, 2.0, 2.1, 4.0, 10.0, 50.0, 500.0, 1000.0],
}


def _exact_rtp(k: int, row: list[float]) -> Fraction:
    return sum(
        coeff * Fraction(str(m)) for coeff, m in zip(base_coeff(k), row)
    )


def _validate() -> None:
    prev_max = 2.6  # classic pick_1 lattice max
    for k, row in sorted(CLASSIC_OFF.items()):
        hud = CLASSIC_HUD[k]
        assert len(row) == k + 1, f"pick_{k}: row length {len(row)} != {k + 1}"

        # 0.1x grid: LUT payout = int(round(m * 100)) must be a multiple of 10.
        for h, m in enumerate(row):
            assert m == 0.0 or abs(m * 10 - round(m * 10)) < 1e-9, (
                f"pick_{k} h={h}: {m} is off the 0.1x lattice"
            )

        # Shape: same zero prefix as the HUD (same first paying hit).
        assert [m == 0 for m in row] == [m == 0 for m in hud], (
            f"pick_{k}: zero prefix diverges from the Classic HUD shape"
        )

        paying = [m for m in row if m > 0]
        assert all(b > a for a, b in zip(paying, paying[1:])), (
            f"pick_{k}: ladder is not strictly increasing: {row}"
        )

        # Maxes copied from the HUD (pick_2 excepted: 5.0 cannot land in the
        # window on the 0.1x grid, so the published snap moves 5.0 -> 5.4).
        expected_max = 5.4 if k == 2 else max(hud)
        assert max(row) == expected_max, (
            f"pick_{k}: max {max(row)} != designed max {expected_max}"
        )
        assert max(row) > prev_max, (
            f"pick_{k}: max {max(row)} does not exceed pick_{k - 1} max {prev_max}"
        )
        prev_max = max(row)

        # Do not flatten jackpot-shaped HUD cells (40x and up) into the max.
        # Pick 2's designed 5.4 is the only max exception; body cells whose
        # HUD value is already a cliff stay on the HUD.
        for h, (m, hm) in enumerate(zip(row, hud)):
            if h == k:
                continue
            if hm >= 40:
                assert m == hm, (
                    f"pick_{k} h={h}: jackpot-shaped HUD {hm} moved to {m}"
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


def classic_off_summary() -> str:
    lines = []
    for k, row in sorted(CLASSIC_OFF.items()):
        cells = " / ".join(f"{m:g}" for m in row if m > 0)
        hud = CLASSIC_HUD[k]
        stats = base_stats(k, row)
        hud_max = 5.4 if k == 2 else max(hud)
        lines.append(
            f"classic_pick_{k:<2d} [{cells}] "
            f"rtp={float(_exact_rtp(k, row)):.6f} "
            f"std={stats['std']:.3f} hr={stats['hit_rate']:.4f} "
            f"etl={stats['etl_sum']:.3f} max={max(row):g} hud_max={hud_max:g}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(classic_off_summary())
