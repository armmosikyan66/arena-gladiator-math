"""Tower game events emitted to the book (and therefore the front-end)."""

from enum import Enum

from src.events.events import *

from game_calculations import round_coefficient


class TowerEventConstants(Enum):
    SESSION_START = "sessionStart"
    TILE_REVEAL = "tileReveal"
    MINE_HIT = "mineHit"
    CASH_OUT = "cashOut"


def session_start_event(
    gamestate,
    difficulty: str,
    rows: int,
    cols: int,
    mines: int,
    win_count: int = None,
    row_steps=None,
    bonuses=None,
    coefficient: float = 1.0,
    payout_multiplier: float = 1.0,
    status: str = "ACTIVE",
    mine_layout=None,
    row_bonuses=None,
    multipliers=None,
):
    """Announce the start of a tower session with difficulty + mine layout.

    ``mineLayout`` is the Stake-selected outcome for this book (list of mine
    index lists per row). Fairness = which book RGS picked via Stake Fair API;
    do not attach custom seed hashes here.

    ``multipliers`` (optional) publishes the base cashout ladder for this
    session (no bonuses) so the client can render the per-row payout preview
    server-authoritatively — it never computes the ladder itself.

    ``rowBonuses`` (optional, live play only) carries the server's pre-resolved
    bonus placements ``{row: {cellIndex, multiplier, coefficient} | null}`` so
    the client can reveal missed bonuses on a loss and display the boosted
    payout with zero arithmetic (``coefficient = base[row] × multiplier``).
    Book sims omit it (bonuses off).

    Initial values: ``coefficient`` 1× and ``payoutMultiplier`` 1.0
    (book root integer 100). Client shows payout = bet.
    """
    event = {
        "index": len(gamestate.book.events),
        "type": TowerEventConstants.SESSION_START.value,
        "difficulty": difficulty,
        "rows": rows,
        "cols": cols,
        "mines": mines,
        "coefficient": coefficient,
        "payoutMultiplier": payout_multiplier,
        "status": status,
    }
    if win_count is not None:
        event["winCount"] = win_count
    if row_steps is not None:
        event["rowSteps"] = list(row_steps)
    if multipliers is not None:
        event["multipliers"] = [
            round_coefficient(float(m)) for m in multipliers
        ]
    if bonuses is not None:
        event["bonuses"] = bonuses
    if mine_layout is not None:
        event["mineLayout"] = [
            sorted(int(t) for t in row) for row in mine_layout
        ]
    if row_bonuses is not None:
        event["rowBonuses"] = {
            int(row): (
                None
                if placed is None
                else {
                    "cellIndex": int(placed["cellIndex"]),
                    "multiplier": float(placed["multiplier"]),
                    **(
                        {"coefficient": float(placed["coefficient"])}
                        if placed.get("coefficient") is not None
                        else {}
                    ),
                }
            )
            for row, placed in row_bonuses.items()
        }
    gamestate.book.add_event(event)


def tile_reveal_event(
    gamestate,
    row: int,
    tile: int,
    is_mine: bool,
    coefficient: float = None,
    bonus_multiplier: float = None,
):
    """Report a revealed tile; a mine ends the session.

    ``coefficient`` is the running multiplier after this reveal (frozen on
    mine hit). ``bonus_multiplier`` is set when the player picked a bonus cell.
    """
    event = {
        "index": len(gamestate.book.events),
        "type": (
            TowerEventConstants.MINE_HIT.value
            if is_mine
            else TowerEventConstants.TILE_REVEAL.value
        ),
        "row": row,
        "tile": int(tile),
        "isMine": is_mine,
    }
    if coefficient is not None:
        event["coefficient"] = coefficient
    if bonus_multiplier is not None and bonus_multiplier > 1:
        event["bonusMultiplier"] = bonus_multiplier
    gamestate.book.add_event(event)


def cash_out_event(gamestate, row: int, multiplier: float, win: float):
    """Report the cashout: last cleared row, its multiplier and the total win.

    This is the session's bet event — emitted only when the outcome is known
    (cash-out / mine / cleared top). ``payout`` is the win in Stake units
    (bet × multiplier), matching the RGS cashOut event shape.
    """
    win_int = int(round(win * 100, 0))
    event = {
        "index": len(gamestate.book.events),
        "type": TowerEventConstants.CASH_OUT.value,
        "row": row,
        "multiplier": multiplier,
        "payout": win_int,
        "totalWin": win_int,
    }
    gamestate.book.add_event(event)
