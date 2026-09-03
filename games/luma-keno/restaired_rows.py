"""Rows that have been restaired by hand and are pinned under the shape lock.

The solver optimises RTP, not readability. Left alone it closes its remaining
RTP gap on whichever body cell carries the most probability mass, which is how
a column ends up reading 7.4 / 8.9 / 9.0 or 1.9 / 2.0 / 2.1 and then cliffing.
A row listed here overrides the solver for that one (section, risk, pick), and
`row_for` refuses to hand it back unless it still passes `shape_lock`.

Values are stored in the chart's own design units - base-bet for Off and Earn,
cost units for the buy chips - which is the same convention `shape_report.grade`
uses, so a row can be pasted between the two without rescaling.

Adding a row here is a deliberate act: it freezes a HUD column against
re-solving. Removing one hands the column back to the solver, packing included.
"""

from __future__ import annotations

from shape_lock import lock_for, violations

#: (section, risk, pick) -> paying cells, lowest paying hit first.
#: The full row is rebuilt as zeros followed by these cells.
RESTAIRED: dict[tuple[str, str, int], list[float]] = {
    # Was 1 / 1.3 / 1.8 / 2.5 / 7 / 40 / 120 / 1000: hits 3-6 climbed 1.30x,
    # 1.38x, 1.39x - three steps the HUD renders as one flat block - and then
    # 7 -> 40 cliffed. Consolation now stops at 0.9x (a refund, per UKGC 14C)
    # and every win above it steps >= 2.5x. Advertised top holds 1000x, which
    # is what keeps Earn classic level with Off classic at pick 10.
    ("earn", "classic", 10): [0.7, 0.9, 2.3, 6.0, 16.0, 45.0, 120.0, 1000.0],
    # Was 1 / 4.4 / 28.4 / 79.8 / 120 / 1000 at the flat 1000x pin: 80 -> 120
    # was a 1.48x mid pair the HUD renders as one cell, and the body packed
    # onto hit 6 (41.8% of return). Restaired to the uniform ~2.7x ladder at
    # the Off-matching 900x top (8/8 750 < 9/9 900 < 10/10 1000; How-to 3600).
    # solve_row output, lock-clean, rtp 0.9634 inside the window.
    ("earn", "classic", 9): [2.0, 5.8, 15.9, 42.3, 112.5, 900.0],
    # Earn high 8 was solver-packed at the 6100 pin: 30.3 -> 324.7 was a
    # 10.72x mid cliff and the last catch 18.79x broke the 8-15x band. The
    # restair moves the wall to 0.5 -> 8.7 (17.4x wall allowance) and holds
    # the last catch at exactly 15x. Lock-clean, rtp 0.9651.
    ("earn", "high", 8): [0.2, 0.5, 8.7, 52.0, 406.7, 6100.0],
    # Earn high 9 at the new 12500 pin: solver rows pack the 6->7 body pair,
    # this uniform ~5-6x ladder keeps the last catch at 15x. How-to 50000
    # > Off 40000. Lock-clean, rtp 0.9654.
    ("earn", "high", 9): [0.6, 4.7, 23.5, 129.6, 833.4, 12500.0],
    # Earn high 10 at the 25000 cap-pinned top (How-to 100000 = the ceiling,
    # so the fleet report grades the final catch as an ordinary step, max 8x).
    # First restair ended 1703.9 -> 25000 (14.67x) - clean under the plain
    # lock's 8-15x last-catch band, a cliff under the capped one. solve_row
    # under the capped lock builds a uniform ~6x ladder ending 3125 -> 25000
    # at exactly 8x. Lock-clean (capped, pick-aware), rtp 0.9655.
    ("earn", "high", 10): [0.3, 0.8, 12.2, 74, 451, 3125, 25000.0],
    # Earn high 5 was 1.6 / 2.1 / 439.3: the 4-of-5 body cell parked at 2.1x
    # (below a real win) and then cliffed 209x into the jackpot. Lowering the
    # top to the How-to floor (229.3, settles 917.2 >= Off 900) funds a real
    # 3-cell ladder: 2.4 -> 15.5 -> 229.3, last step 14.8x. rtp 0.9653.
    ("earn", "high", 5): [2.4, 15.5, 229.3],
    # Earn high 6 was 1.0 / 1.3 / 1.8 / 2028.7: three sub-2x consolation cells
    # then a 1127x cliff. 552.8 (How-to 2211.2 >= Off 2200) funds
    # 0.5 / 7.5 / 49.7 -> 552.8, last 11.1x. rtp 0.9645.
    ("earn", "high", 6): [0.5, 7.5, 49.7, 552.8],
    # Earn high 7 was 0.8 / 2.2 / 9.2 / 75.8 / 4582: a 60x last catch on top
    # of an already-cliffing 8.24x mid pair. 1468.8 (How-to 5875.2 >= Off
    # 5500) keeps the 8x wall once and ends 144.1 -> 1468.8 (10.2x). rtp 0.9642.
    ("earn", "high", 7): [0.3, 2.4, 19.2, 144.1, 1468.8],
    # buy10 low rows, in cost units (1.0 = chip price back). The solver's
    # water-fill packs sub-refund consolation bodies (0.09/0.1, 0.98/1.06)
    # the HUD renders as one cell. Pick 3's top cannot reach the Off pin
    # (1.04 cost units is 147% RTP with placed Lumen) or even exceed pick 2;
    # 0.26 matches pick 2 so the ladder is flat there, not inverted.
    ("buy10", "low", 3): [0.02, 0.14, 0.26],
    ("buy10", "low", 6): [0.02, 0.07, 0.4, 0.71, 4.0],
    ("buy10", "low", 9): [0.16, 0.24, 0.67, 0.84, 1.06, 8.5],
    ("buy10", "low", 10): [0.08, 0.23, 0.51, 0.79, 1.0, 1.25, 10.0],
}


def row_for(
    section: str, risk: str, k: int, cost: float = 1.0
) -> list[float] | None:
    """Pinned row for this chart in design units, or None if it is not pinned.

    Raises if the pinned row no longer satisfies the lock, so a lock change can
    never silently ship a column it would now reject.
    """
    cells = RESTAIRED.get((section, risk, k))
    if cells is None:
        return None
    row = [0.0] * (k + 1 - len(cells)) + list(cells)
    label = f"{section}.{risk}.{k}"
    errs = violations(row, k, lock=lock_for(cost), label=label)
    if errs:
        raise AssertionError(f"pinned row no longer lock-clean: {errs}")
    return row


def scaled_row_for(
    section: str, risk: str, k: int, cost: float = 1.0
) -> list[float] | None:
    """`row_for` converted back into the base-bet units paytables.json stores."""
    row = row_for(section, risk, k, cost)
    if row is None:
        return None
    return [round(m * cost, 6) for m in row]
