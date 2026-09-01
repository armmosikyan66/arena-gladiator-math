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
