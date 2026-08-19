"""Interactive tower session state machine (source of truth for live play).

Flow
----
1. ``start_session`` — open a round, generate mine layout, coefficient = 1
2. ``pick_tile`` — resolve one row; advance coefficient or end on mine
3. ``cash_out`` — lock win from current state (bet × coefficient)

Book sims use ``rng`` so each published book is a fixed layout+path.
Live play must use ``mineLayout`` from the Stake-selected session book
(Fair API verifies which book/payout was selected — not a custom HMAC).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from game_calculations import (
    DEFAULT_MAX_PAYOUT,
    SESSION_BONUS_CHANCE,
    build_multipliers,
    build_play_ladder,
    build_row_steps,
    clamp_win_to_cap,
    generate_mine_layout,
    mines_for,
    next_coefficient,
    pick_bonus_cell,
    profit_from_coefficient,
    roll_bonus,
    round_coefficient,
    steps_from_multipliers,
)


@dataclass
class TowerSession:
    """Mutable in-progress (or finished) tower round."""

    difficulty: str
    bet_amount: float
    cols: int
    rows: int
    win_count: int
    mines: int
    row_steps: list
    mine_layout: list  # list[set[int]] per row
    coefficient: float = 1.0
    current_row: int = 0  # next row to play
    status: str = "ACTIVE"  # ACTIVE | CASHED_OUT | LOST | CLEARED
    picks: list = field(default_factory=list)  # {row, tile, is_mine, coefficient}
    payout_multiplier: float = 1.0  # 1× at open; locked on terminal win
    win_amount: float = 0.0  # bet at open; bet × multiplier when settled
    # Bonus tables keyed by row index → {multiplier: odds}. Empty for book sims.
    bonuses: dict = field(default_factory=dict)
    # Resolved per-row bonus placement: row → {cellIndex, multiplier}.
    row_bonuses: dict = field(default_factory=dict)
    # Session-level bonus gate result (None = gate disabled → per-row 1/N rolls;
    # True = this session gets a bonus on every bonus row; False = none).
    bonus_session: Optional[bool] = None
    # Dollar win ceiling (Stake/operator maxWinning). Cashout never exceeds this.
    max_payout: float = DEFAULT_MAX_PAYOUT
    full_rows: int = 0  # published tower height before win-cap truncate
    # Cashout ladder for this session (must match client display).
    multipliers: list = field(default_factory=list)

    @property
    def revealed_rows(self) -> int:
        return self.current_row

    def layout_public(self) -> list:
        """Mine layout as JSON-safe sorted lists (for books / clients)."""
        return [sorted(list(row)) for row in self.mine_layout]

    def to_public_dict(self) -> dict:
        """Safe snapshot for clients (no mine layout while ACTIVE)."""
        data = {
            "difficulty": self.difficulty,
            "betAmount": self.bet_amount,
            "cols": self.cols,
            "rows": self.rows,
            "winCount": self.win_count,
            "mines": self.mines,
            "rowSteps": list(self.row_steps),
            "coefficient": self.coefficient,
            "currentRow": self.current_row,
            "status": self.status,
            "payoutMultiplier": self.payout_multiplier,
            "winAmount": self.win_amount,
            "picks": list(self.picks),
        }
        if self.bonus_session is not None:
            data["bonusSession"] = self.bonus_session
        if self.status != "ACTIVE":
            data["layout"] = self.layout_public()
        return data


def start_session(
    difficulty: str,
    bet_amount: float,
    mode: dict,
    rng,
    mine_layout: Optional[list] = None,
    max_payout: Optional[float] = None,
    allowed_rows: Optional[int] = None,
) -> TowerSession:
    """Open a new ACTIVE session and draw (or accept) the mine layout.

    Prefer a layout already chosen for a published book. Otherwise sample
    with ``rng`` during book generation.

    Live play: pass ``max_payout`` (and optionally ``allowed_rows``).
    Multipliers are auto-calculated from fair odds + house edge, then
    truncated so ``bet × topMult ≤ maxWinning``. Book sims omit both.
    """
    bet = float(bet_amount)
    cols = int(mode["cols"])
    win_count = int(mode["winCount"])
    full_rows = int(mode["rows"])
    mines = int(mode.get("mines", mines_for(cols, win_count)))

    win_cap = (
        float(max_payout)
        if max_payout is not None and float(max_payout) > 0
        else float(mode.get("maxPayout") or DEFAULT_MAX_PAYOUT)
    )

    full_steps = build_row_steps(cols, win_count, full_rows)
    full_mults = build_multipliers(cols, win_count, full_rows)

    apply_cap = allowed_rows is not None or (
        max_payout is not None and float(max_payout) > 0
    )
    if apply_cap:
        ladder = build_play_ladder(
            bet=bet,
            max_winning=win_cap,
            difficulty=difficulty,
            cols=cols,
            win_count=win_count,
            rows=full_rows,
            max_bet=float(mode.get("maxBet") or 10.0),
            bonuses=mode.get("bonuses") or {},
        )
        rows = (
            max(1, min(int(allowed_rows), full_rows))
            if allowed_rows is not None
            else ladder["rows"]
        )
        mults = list(ladder["multipliers"][:rows]) if allowed_rows is None else full_mults[:rows]
        steps = list(ladder["rowSteps"][:rows]) if allowed_rows is None else steps_from_multipliers(mults)
    else:
        rows = full_rows
        mults = full_mults[:rows]
        steps = full_steps[:rows]

    if mine_layout is not None:
        layout = [set(int(t) for t in row) for row in mine_layout][:rows]
    else:
        layout = generate_mine_layout(cols, rows, mines, rng)

    raw_bonuses = mode.get("bonuses") or {}
    bonuses = {
        int(row_idx): {
            int(mult): int(odds) for mult, odds in table.items()
        }
        for row_idx, table in raw_bonuses.items()
        if int(row_idx) < rows
    }
    # Session-level bonus gate: one roll decides whether this session has any
    # bonus. None (SESSION_BONUS_CHANCE disabled) → per-row independent 1/N.
    bonus_session: Optional[bool] = None
    if SESSION_BONUS_CHANCE is not None and rng is not None and bonuses:
        bonus_session = rng.random() < float(SESSION_BONUS_CHANCE)
    session = TowerSession(
        difficulty=difficulty,
        bet_amount=bet,
        cols=cols,
        rows=rows,
        win_count=win_count,
        mines=mines,
        row_steps=list(steps),
        mine_layout=layout,
        payout_multiplier=1.0,
        win_amount=bet,
        bonuses=bonuses,
        max_payout=win_cap,
        full_rows=full_rows,
        multipliers=list(mults),
        bonus_session=bonus_session,
    )
    # Pre-resolve every bonus row at session open so the full bonus layout is
    # known upfront. This lets the client reveal missed bonuses on a loss and
    # is identical to lazy resolution (same RNG order — pick_tile consumes no
    # RNG outside _resolve_row_bonus, which is idempotent per row).
    for row in list(bonuses.keys()):
        _resolve_row_bonus(session, row, rng)
    return session


def _resolve_row_bonus(
    session: TowerSession, row: int, rng
) -> Optional[dict]:
    """Roll/place the bonus for ``row`` once; return {cellIndex, multiplier} or None."""
    if row in session.row_bonuses:
        return session.row_bonuses[row]

    table = session.bonuses.get(row)
    if not table or rng is None:
        return None

    # Session-level gate overrides per-row independent rolls.
    #   False → no bonus this session (any row).
    #   True  → force a bonus on every bonus row (skip the 1/N roll).
    #   None  → gate disabled, use per-row 1/N (docs spec).
    if session.bonus_session is False:
        session.row_bonuses[row] = None
        return None
    forced = session.bonus_session is True
    if forced:
        rolled = float(
            max(int(m) for m, odds in table.items() if odds and int(odds) > 0)
        )
    else:
        rolled = roll_bonus(table, rng)
        if rolled is None:
            session.row_bonuses[row] = None
            return None

    winning = [
        c for c in range(session.cols) if c not in session.mine_layout[row]
    ]
    if not winning:
        session.row_bonuses[row] = None
        return None

    placed = {
        "cellIndex": pick_bonus_cell(winning, rng),
        "multiplier": float(rolled),
    }
    session.row_bonuses[row] = placed
    return placed


def resolve_row_bonus(
    session: TowerSession, row: int, rng
) -> Optional[dict]:
    """Public API: pre-resolve a row's bonus so it can be handed to the client.

    This is the single source of truth for bonus placement (the client must
    never roll/place a bonus itself). Calling this populates
    ``session.row_bonuses[row]`` with ``{cellIndex, multiplier}`` (or ``None``
    when no bonus appears), and the same dict is returned. Idempotent per row.
    """
    return _resolve_row_bonus(session, row, rng)


def resolved_row_bonuses(session: TowerSession) -> dict:
    """Export resolved per-row bonus placements for the client.

    Returns a JSON-safe ``{row: {cellIndex, multiplier, coefficient} | null}`` map
    keyed by row index (int). ``coefficient`` is the bonus-inclusive value for
    that bonus cell = ``base[row] × multiplier`` (from the published ladder), so
    the client can display the boosted payout with zero arithmetic. Only rows
    already resolved appear; the client treats a missing row as "no bonus
    resolved yet".
    """
    out = {}
    mults = list(getattr(session, "multipliers", None) or [])
    for row, placed in (session.row_bonuses or {}).items():
        if placed is None:
            out[int(row)] = None
            continue
        cell = int(placed["cellIndex"])
        mult = float(placed["multiplier"])
        entry: dict = {"cellIndex": cell, "multiplier": mult}
        if 0 <= int(row) < len(mults):
            base = float(mults[int(row)])
            entry["coefficient"] = round_coefficient(base * mult)
        out[int(row)] = entry
    return out


def pick_tile(
    session: TowerSession,
    row: int,
    tile: int,
    *,
    rng=None,
    apply_bonuses: bool = False,
) -> dict:
    """Resolve a pick on the active row. Returns a result dict for events/UI.

    When ``apply_bonuses`` is True (live climb), a safe pick on a bonus row
    may land on the bonus cell (e.g. ×2) and multiply the coefficient.
    Book settle sims keep ``apply_bonuses=False`` so ladder LUTs stay fixed.
    """
    if session.status != "ACTIVE":
        raise ValueError(f"Session is {session.status}, cannot pick")
    if row != session.current_row:
        raise ValueError(f"Must pick row {session.current_row}, got {row}")
    if tile < 0 or tile >= session.cols:
        raise ValueError("Tile out of bounds")

    is_mine = tile in session.mine_layout[row]
    result: dict[str, Any] = {
        "row": row,
        "tile": tile,
        "is_mine": is_mine,
        "coefficient": session.coefficient,
        "bonus_multiplier": None,
        "status": session.status,
    }

    if is_mine:
        session.status = "LOST"
        session.payout_multiplier = 0.0
        session.win_amount = 0.0
        session.picks.append(
            {
                "row": row,
                "tile": tile,
                "isMine": True,
                "coefficient": session.coefficient,
            }
        )
        result["status"] = session.status
        return result

    bonus_mult = 1.0
    if apply_bonuses and session.bonuses:
        placed = _resolve_row_bonus(session, row, rng)
        if placed and tile == placed["cellIndex"]:
            bonus_mult = float(placed["multiplier"])
            result["bonus_multiplier"] = bonus_mult

    step = session.row_steps[row]
    prior_bonus_product = 1.0
    for p in session.picks:
        bm = float(p.get("bonusMultiplier") or 0)
        if bm > 1:
            prior_bonus_product *= bm
    bonus_product = prior_bonus_product * (bonus_mult if bonus_mult > 1 else 1.0)

    # Always anchor to the published ladder cell for this row, then apply the
    # product of all collected bonuses (including this pick).
    #   2.8 × 2 = 5.6  (not prev×step×2 → 5.7 from pre-floor drift)
    #   after ×2 on an earlier row, next ladder 2.8 → still 2.8×2 = 5.6
    if session.multipliers and row < len(session.multipliers):
        base = float(session.multipliers[row])
        session.coefficient = round_coefficient(base * bonus_product)
    else:
        session.coefficient = next_coefficient(
            session.coefficient, step, bonus_mult
        )
    # Cap to maxWinning/bet so bonuses never push payout past the win cap.
    # Each row's effective multiplier ≤ maxWinning / bet (e.g. $10k/$1k = 10×).
    if session.bet_amount > 0 and session.max_payout > 0:
        max_mult = round_coefficient(session.max_payout / session.bet_amount)
        if session.coefficient > max_mult:
            session.coefficient = max_mult
    session.current_row = row + 1
    pick_record = {
        "row": row,
        "tile": tile,
        "isMine": False,
        "coefficient": session.coefficient,
    }
    if bonus_mult > 1:
        pick_record["bonusMultiplier"] = bonus_mult
    session.picks.append(pick_record)
    result["coefficient"] = session.coefficient
    result["status"] = session.status

    if session.current_row >= session.rows:
        # Cleared the tower — auto cash out at top, keep pick fields for events.
        settlement = cash_out(session)
        result.update(settlement)
        result["is_mine"] = False
        result["row"] = row
        result["tile"] = tile
        result["coefficient"] = session.coefficient
        result["status"] = session.status
        if bonus_mult > 1:
            result["bonus_multiplier"] = bonus_mult
        return result

    return result


def cashout_multiplier(session: TowerSession) -> float:
    """Ladder[cleared] × product of collected bonuses (e.g. 2.8 × 2 = 5.6)."""
    if session.current_row <= 0:
        return 0.0
    cleared = session.current_row - 1
    prod = 1.0
    for p in session.picks:
        bm = float(p.get("bonusMultiplier") or 0)
        if bm > 1:
            prod *= bm
    if session.multipliers and cleared < len(session.multipliers):
        return round_coefficient(float(session.multipliers[cleared]) * prod)
    return round_coefficient(session.coefficient)


def cash_out(session: TowerSession) -> dict:
    """Lock the win from current session state and mark terminal.

    Win is only paid when at least one row was cleared.
    ``payout_multiplier`` is the coefficient (Stake hundredths = ×100).
    ``win_amount`` is bet × coefficient (total return, not profit).
    Cashout uses ladder × collected bonuses so a ×2 on a 2.8 ladder pays 5.6,
    not the bare ladder 2.8.
    """
    if session.status in ("CASHED_OUT", "CLEARED"):
        return _settlement_result(session)
    if session.status == "LOST":
        return _settlement_result(session)
    if session.status != "ACTIVE":
        raise ValueError(f"Cannot cash out from {session.status}")

    if session.current_row <= 0:
        raise ValueError("Cannot cash out before clearing a row")

    locked = cashout_multiplier(session)
    if locked > 0:
        session.coefficient = locked

    # Hard cap: bonuses can push coefficient past bet×ladder ≤ maxWinning.
    win, mult = clamp_win_to_cap(
        session.bet_amount,
        round_coefficient(session.coefficient),
        session.max_payout,
    )
    session.payout_multiplier = mult
    session.win_amount = win
    session.coefficient = mult
    session.status = (
        "CLEARED" if session.current_row >= session.rows else "CASHED_OUT"
    )
    return _settlement_result(session)


def _settlement_result(session: TowerSession) -> dict:
    profit = profit_from_coefficient(session.bet_amount, session.payout_multiplier)
    return {
        "status": session.status,
        "coefficient": session.coefficient,
        "payout_multiplier": session.payout_multiplier,
        "payout_multiplier_int": int(round(session.payout_multiplier * 100, 0)),
        "win_amount": session.win_amount,
        "profit": profit,
        "revealed_rows": session.current_row,
        "bet_amount": session.bet_amount,
    }


def payout_units(session: TowerSession, amount_units: int) -> int:
    """Stake-style integer payout from locked multiplier and bet in units."""
    if session.status == "LOST" or session.payout_multiplier <= 0:
        return 0
    mult_int = int(round(session.payout_multiplier * 100, 0))
    return int(round((amount_units * mult_int) / 100))
