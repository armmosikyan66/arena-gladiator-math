"""Pure math for the tower game: row steps, bonuses, cashout multipliers and RTP.

Multi-step climb:

* Each difficulty has its own row count, columns and safe-tile count.
* Cashout multipliers are auto-calculated from fair odds × depth house edge:
      step[i] = (cols / winCount) × (1 − (0.01 + i × 0.002))
      mult[i] = product of steps[0..i]   (floored to 0.1×)
* Operator ``maxWinning`` does **not** rewrite mid-ladder values — it only
  truncates playable rows so ``bet × mult ≤ maxWinning``, and hard-caps cashout.
* Clearing a row advances the running coefficient by that row's step,
  optionally × bonus.
* Coefficients are floored to 0.1× for Stake payoutMultiplier format.
"""

from math import floor

from src.executables.executables import Executables

# Base house edge + per-row growth (matches FE / README).
BASE_HOUSE_EDGE = 0.01
EDGE_GROWTH = 0.002

# Bet modes — cols / win_count / rows match BitKong DEFAULT_ECONOMY.
DIFFICULTIES = {
    "easy": {"label": "Easy", "cols": 4, "win_count": 3, "rows": 9},
    "medium": {"label": "Medium", "cols": 3, "win_count": 2, "rows": 9},
    "hard": {"label": "Hard", "cols": 2, "win_count": 1, "rows": 9},
    "extreme": {"label": "Extreme", "cols": 3, "win_count": 1, "rows": 7},
    "nightmare": {"label": "Nightmare", "cols": 4, "win_count": 1, "rows": 6},
}

# Default bonus placement — rows 3 / 6 / 9 (0-indexed 2 / 5 / 8).
# Map: multiplier → odds denominator (1-in-N).  Chance = 1/N.
# docs/stake-engine-game-math.md (Bitkong defaults):
#   row 3 → ×2  (1-in-10)  P_exists = 10.0%
#   row 6 → ×5  (1-in-7)   P_exists = 14.29%
#   row 9 → ×10 (1-in-5)   P_exists = 20.0%
DEFAULT_BONUSES = {
    2: {2: 10},   # row 3: ×2, 1-in-10 → 10%   (Bitkong default)
    5: {5: 7},    # row 6: ×5, 1-in-7  → 14.29% (Bitkong default)
    8: {10: 5},   # row 9: ×10, 1-in-5 → 20%   (Bitkong default)
}

# Session-level bonus gate — chance that a given session contains ANY bonus.
#   None  → disabled: use per-row independent 1/N rolls (docs spec, production).
#   float → that fraction of sessions contain bonuses. When the gate passes,
#           EVERY bonus row gets a bonus (forced); when it fails, none do.
SESSION_BONUS_CHANCE = None

# Operator max win ($). Truncates tower height; does not reshape the ladder.
DEFAULT_MAX_PAYOUT = 10_000.0
DEFAULT_MAX_BET = 10.0
DEFAULT_MIN_BET = 1.0
MIN_PLAYABLE_ROWS = 1


def round7(value: float) -> float:
    """Round to 7 decimals — keeps published ladders clean."""
    return round(value * 1e7) / 1e7


def round_coefficient(value: float):
    """Floor to 1 decimal place (0.1× steps).

    Stake RGS requires ``payoutMultiplier`` (value × 100) to be a multiple of
    10 — i.e. multipliers in 0.1× increments. Using 2dp (e.g. 11.12 → 1112)
    fails publish with payout-format errors.
    """
    return floor(value * 10) / 10


def mines_for(cols: int, win_count: int) -> int:
    return cols - win_count


def win_chance(cols: int, win_count: int) -> float:
    """Probability that a randomly revealed tile on a level is safe."""
    return win_count / cols


def fair_multiplier(cols: int, win_count: int) -> float:
    """Statistically fair per-row multiplier (= 1 / win_chance)."""
    return cols / win_count


def build_row_steps(
    cols: int,
    win_count: int,
    rows: int,
    house_edge: float = BASE_HOUSE_EDGE,
    edge_growth: float = EDGE_GROWTH,
) -> list:
    """Per-row coefficient steps from fair odds × depth house edge."""
    steps = []
    fair = fair_multiplier(cols, win_count)
    for i in range(max(1, int(rows))):
        edge = float(house_edge) + i * float(edge_growth)
        steps.append(round7(fair * (1.0 - edge)))
    return steps


def steps_from_multipliers(multipliers: list) -> list:
    """Per-row coefficient steps = ratio between consecutive cashout mults."""
    steps = []
    prev = 1.0
    for mult in multipliers:
        m = float(mult)
        steps.append(round7(m / prev) if prev > 0 else 1.0)
        prev = m
    return steps


def next_coefficient(
    coefficient: float, row_step: float, bonus_multiplier: float = 1.0
) -> float:
    """Advance the running coefficient by one cleared row."""
    return round_coefficient(coefficient * row_step * bonus_multiplier)


def build_multipliers(
    cols: int,
    win_count: int,
    rows: int,
    house_edge: float = BASE_HOUSE_EDGE,
    edge_growth: float = EDGE_GROWTH,
) -> list:
    """Cashout multipliers after each cleared row (no bonuses), floored."""
    steps = build_row_steps(cols, win_count, rows, house_edge, edge_growth)
    multipliers = []
    acc = 1.0
    for step in steps:
        acc = next_coefficient(acc, step, 1.0)
        multipliers.append(acc)
    return multipliers


def build_multipliers_for_stake(
    cols: int,
    win_count: int,
    max_rows: int,
    bet: float,
    max_winning: float = DEFAULT_MAX_PAYOUT,
    min_rows: int = MIN_PLAYABLE_ROWS,
) -> list:
    """Fair-odds ladder trimmed so ``bet × mult ≤ max_winning``."""
    full = build_multipliers(cols, win_count, max_rows)
    n = allowed_rows_for_bet(bet, full, max_winning, min_rows)
    return full[:n]


def resolve_difficulty_geometry(
    difficulty: str | None = None,
    cols: int | None = None,
    win_count: int | None = None,
    rows: int | None = None,
) -> tuple:
    """Resolve ``(cols, win_count, rows)`` from a difficulty name or explicit args."""
    if difficulty:
        d = DIFFICULTIES[str(difficulty).lower()]
        return int(d["cols"]), int(d["win_count"]), int(d["rows"])
    if cols is None or win_count is None or rows is None:
        raise ValueError("Need difficulty or cols/win_count/rows")
    return int(cols), int(win_count), int(rows)


def profit_from_coefficient(bet: float, coefficient: float) -> float:
    """Profit for a cashed-out round; 0 when coefficient never moved past 1."""
    if coefficient <= 1:
        return 0.0
    return round_coefficient(bet * coefficient - bet)


def session_rtp(cols: int, win_count: int, rows: int) -> float:
    """Design RTP for play-to-top (no early cashout, no bonuses).

    ``sessionRtp ≈ (winChance)^rows × topMult``.
    """
    chance = win_chance(cols, win_count)
    mults = build_multipliers(cols, win_count, rows)
    top = mults[-1] if mults else 1.0
    return round((chance**rows) * top, 4)


def product_of_bonuses(bonuses: dict) -> float:
    """Product of every bonus multiplier in a difficulty's bonus table.

    Worst-case climb hits every bonus row, so the running coefficient can grow
    to ``baseTop × product_of_bonuses``. The base ladder top ``Y`` must satisfy
    ``Y × product(bonuses) ≤ maxWinning / bet``.
    """
    if not bonuses:
        return 1.0
    prod = 1.0
    for table in bonuses.values():
        if not table:
            continue
        prod *= float(max(int(m) for m in table.keys()))
    return prod


def allowed_rows_for_bet(
    bet: float,
    multipliers: list,
    max_payout: float = DEFAULT_MAX_PAYOUT,
    min_rows: int = MIN_PLAYABLE_ROWS,
    bonus_product: float = 1.0,
) -> int:
    """How many tower rows this stake may climb under a max-win cap.

    The base ladder top ``Y`` must satisfy ``Y × product(bonuses) ≤ maxWin/bet``,
    so the effective base cap is ``(maxWin/bet) / bonus_product``. Keep published
    ladder rows whose base multiplier is at or below that cap.
    """
    if not multipliers:
        return min_rows
    full = len(multipliers)
    min_rows = max(1, min(int(min_rows), full))
    if bet is None or bet <= 0 or max_payout is None or max_payout <= 0:
        return full

    bp = float(bonus_product) if bonus_product and bonus_product > 0 else 1.0
    max_base_mult = (float(max_payout) / float(bet)) / bp
    allowed = 0
    for idx, mult in enumerate(multipliers):
        m = float(mult)
        if m <= max_base_mult + 1e-9:
            allowed = idx + 1
        else:
            break

    if allowed <= 0:
        return min_rows
    return max(min_rows, min(allowed, full))


def clamp_max_bet_by_win_cap(
    max_bet: float,
    max_winning: float,
    first_multiplier: float,
    bonus_product: float = 1.0,
) -> float:
    """Clamp maxBet so the base ladder + all bonuses cannot exceed maxWinning.

    Worst case: ``firstBaseMult × product(bonuses)`` on the first playable row.
    ``safeMaxBet = maxWinning / (firstBaseMult × product(bonuses))``.
    """
    if max_bet is None or max_bet <= 0:
        return float(max_bet or 0)
    if max_winning is None or max_winning <= 0 or first_multiplier is None:
        return float(max_bet)
    first = float(first_multiplier)
    if first <= 0:
        return float(max_bet)
    bp = float(bonus_product) if bonus_product and bonus_product > 0 else 1.0
    return min(float(max_bet), float(max_winning) / (first * bp))


def clamp_win_to_cap(bet: float, multiplier: float, max_winning: float) -> tuple:
    """Return ``(win_amount, payout_multiplier)`` capped at maxWinning dollars.

    When bonuses push the running coefficient past the exposure ceiling,
    lock payout at ``max_winning`` and back-solve the multiplier.
    """
    bet = float(bet or 0)
    mult = float(multiplier or 0)
    cap = float(max_winning or 0)
    if bet <= 0 or mult <= 0:
        return 0.0, 0.0
    raw = round_coefficient(bet * mult)
    if cap <= 0 or raw <= cap + 1e-9:
        return raw, round_coefficient(mult)
    capped_mult = round_coefficient(cap / bet)
    # Floor may still overshoot by a cent — keep dollar win ≤ cap.
    win = min(cap, round_coefficient(bet * capped_mult))
    if win > cap:
        win = cap
    return win, capped_mult


def build_play_ladder(
    multipliers=None,
    bet: float = 0.0,
    max_winning: float = DEFAULT_MAX_PAYOUT,
    min_bet: float = 0.0,
    max_bet: float = 0.0,
    min_rows: int = MIN_PLAYABLE_ROWS,
    bonuses: dict | None = None,
    *,
    difficulty: str | None = None,
    cols: int | None = None,
    win_count: int | None = None,
    rows: int | None = None,
) -> dict:
    """Auto-calculate playable multipliers from fair odds + maxWinning truncate.

    Published ladder = fair odds × house edge (per difficulty).
    Base ladder top ``Y`` satisfies ``Y × product(bonuses) ≤ maxWin/bet``;
    rows are truncated where the base multiplier exceeds that cap.
    """
    stake = max(float(bet or 0), float(min_bet or 0), 1.0)
    win_cap = float(max_winning) if max_winning else DEFAULT_MAX_PAYOUT
    ref_max_bet = float(max_bet) if max_bet and max_bet > 0 else DEFAULT_MAX_BET
    bonus_product = product_of_bonuses(bonuses) if bonuses else 1.0

    c, w, r = resolve_difficulty_geometry(difficulty, cols, win_count, rows) if (
        difficulty or (cols is not None and win_count is not None and rows is not None)
    ) else (None, None, None)

    if multipliers is None:
        if c is None or w is None or r is None:
            raise ValueError("Need difficulty or cols/win_count/rows to build ladder")
        published = build_multipliers(c, w, r)
    else:
        published = list(multipliers)
        if r is None:
            r = len(published)

    row_steps = (
        build_row_steps(c, w, len(published))
        if c is not None and w is not None
        else steps_from_multipliers(published)
    )
    n = allowed_rows_for_bet(stake, published, win_cap, min_rows, bonus_product)
    effective = published[:n]
    steps = row_steps[:n]
    top = effective[-1] if effective else 0.0
    max_mult_for_bet = (win_cap / stake) if stake > 0 and win_cap else top
    max_mult_at_max = win_cap / ref_max_bet if win_cap else top
    first = published[0] if published else 1.0
    return {
        "rows": n,
        "fullRows": len(published),
        "multipliers": effective,
        "rowSteps": steps,
        "topMult": top,
        "maxMultForBet": max_mult_for_bet,
        "maxMultAtMaxBet": max_mult_at_max,
        "maxWinning": win_cap,
        "bet": stake,
        "firstMultiplier": first,
        "bonusProduct": bonus_product,
        "safeMaxBet": clamp_max_bet_by_win_cap(
            ref_max_bet, win_cap, first, bonus_product
        ),
    }


def apply_allowed_rows(
    mode: dict,
    bet: float,
    max_payout: float = DEFAULT_MAX_PAYOUT,
    allowed_rows: int | None = None,
) -> dict:
    """Return a shallow mode copy truncated to the stake-allowed row height."""
    multipliers = list(mode.get("multipliers") or [])
    if allowed_rows is not None:
        rows = max(1, min(int(allowed_rows), len(multipliers) or 1))
    else:
        rows = allowed_rows_for_bet(bet, multipliers, max_payout)
    out = dict(mode)
    out["fullRows"] = mode.get("rows", rows)
    out["rows"] = rows
    out["rowSteps"] = list(mode.get("rowSteps") or [])[:rows]
    out["multipliers"] = multipliers[:rows]
    if out["multipliers"]:
        out["maxWin"] = out["multipliers"][-1]
    bonuses = mode.get("bonuses") or {}
    out["bonuses"] = {
        str(k): v
        for k, v in bonuses.items()
        if int(k) < rows
    }
    out["maxPayout"] = float(max_payout or DEFAULT_MAX_PAYOUT)
    return out


def effective_multipliers(multipliers: list, allowed_rows: int) -> list:
    """Slice the cashout ladder to the stake-allowed height."""
    if not multipliers:
        return []
    n = max(1, min(int(allowed_rows), len(multipliers)))
    return list(multipliers[:n])


def bonuses_for_difficulty(rows: int) -> dict:
    """Bonus tables keyed by row index, filtered to rows that exist."""
    return {idx: table for idx, table in DEFAULT_BONUSES.items() if idx < rows}


def bonus_multiplier_by_row(bonuses: dict) -> dict:
    """Map row index → highest configured bonus multiplier."""
    out = {}
    for row, table in (bonuses or {}).items():
        best = 0
        for m, odds in table.items():
            if odds and int(odds) > 0:
                best = max(best, int(m))
        if best > 0:
            out[int(row)] = best
    return out


def enumerate_settle_payouts(multipliers: list, bonuses: dict) -> list:
    """All distinct cashout multipliers: ladder[depth] × collected-bonus product.

    Used to publish Stake settle modes ``{diff}_p{payout×100}`` so a climb that
    collected ×2 on the 2.2 ladder settles at 4.4 (``easy_p440``), not bare 2.2.
    """
    row_bonus = bonus_multiplier_by_row(bonuses)
    bonus_rows = sorted(row_bonus)
    payouts = set()
    for depth in range(1, len(multipliers) + 1):
        ladder = float(multipliers[depth - 1])
        available = [r for r in bonus_rows if r < depth]
        n = len(available)
        for bits in range(1 << n):
            prod = 1.0
            for i in range(n):
                if bits & (1 << i):
                    prod *= row_bonus[available[i]]
            payouts.add(round_coefficient(ladder * prod))
    return sorted(payouts)


def settle_mode_name(difficulty: str, payout: float) -> str:
    """Stake mode name for a fixed cashout payout, e.g. ``easy_p440`` for 4.4×."""
    payout_int = int(round(float(payout) * 100))
    return f"{difficulty}_p{payout_int}"


# --- Bonus probability math (docs/stake-engine-game-math.md) -----------------
# Given a bonus table entry {multiplier: odds_N} on a row with W winning cells
# out of C total, and 0-based row index r:
#   P_exists  = 1 / N            (bonus appears on the row)
#   P_collect = 1 / (N * W)      (player picks the bonus cell, given they survive)
#   P_full    = (W / C)^(r+1) * 1 / (N * W)   (reach row + survive + collect)


def bonus_appears_chance(odds: int) -> float:
    """P_exists — chance a bonus appears on a row.

    With the session-level gate (``SESSION_BONUS_CHANCE`` set), every bonus row
    appears iff the gate passes, so per-row P_exists = the gate chance.
    Otherwise the docs spec: ``1 / N``.
    """
    if SESSION_BONUS_CHANCE is not None:
        return float(SESSION_BONUS_CHANCE)
    n = int(odds)
    if n <= 0:
        return 0.0
    return 1.0 / n


def bonus_collect_chance(odds: int, win_count: int) -> float:
    """P_collect — chance player collects, given they survive.

    ``P_collect = P_exists * (1 / W)``. Gate-aware via ``bonus_appears_chance``.
    """
    w = int(win_count)
    if w <= 0:
        return 0.0
    return bonus_appears_chance(odds) / w


def bonus_full_climb_chance(
    cols: int, win_count: int, row_index: int, odds: int
) -> float:
    """P_full = (W/C)^(r+1) * P_collect — reach row + survive + collect."""
    c = int(cols)
    w = int(win_count)
    r = int(row_index)
    if c <= 0 or w <= 0 or r < 0:
        return 0.0
    return (w / c) ** (r + 1) * bonus_collect_chance(odds, w)


def bonus_chances_for_row(
    bonuses: dict, row: int, cols: int, win_count: int
) -> dict:
    """Per-row bonus chance summary for a single row.

    Returns ``{multiplier, odds, pExists, pCollect, pFull}`` for the highest
    configured multiplier on that row, or ``None`` when the row has no bonus.
    """
    table = (bonuses or {}).get(row) or (bonuses or {}).get(str(row))
    if not table:
        return None
    best_mult = 0
    best_odds = 0
    for m, odds in table.items():
        odds_n = int(odds)
        if odds_n > 0 and int(m) > best_mult:
            best_mult = int(m)
            best_odds = odds_n
    if best_odds <= 0:
        return None
    return {
        "row": int(row),
        "multiplier": best_mult,
        "odds": best_odds,
        "pExists": round(bonus_appears_chance(best_odds), 6),
        "pCollect": round(bonus_collect_chance(best_odds, win_count), 6),
        "pFull": round(
            bonus_full_climb_chance(cols, win_count, int(row), best_odds), 6
        ),
    }


def bonus_chances_for_difficulty(
    bonuses: dict, cols: int, win_count: int, rows: int
) -> list:
    """Per-row bonus chance summary for every bonus row in a difficulty."""
    out = []
    for row in range(rows):
        entry = bonus_chances_for_row(bonuses, row, cols, win_count)
        if entry:
            out.append(entry)
    return out


def generate_mine_layout(cols: int, rows: int, mines: int, rng) -> list:
    """Random mine positions per level, one ``set`` of deadly tile indices each."""
    return [set(rng.sample(range(cols), mines)) for _ in range(rows)]


def roll_bonus(bonus_table: dict, rng) -> float | None:
    """Roll a row's bonus table; highest triggered multiplier wins, or None."""
    if not bonus_table:
        return None
    chosen = None
    for mult in sorted(bonus_table.keys()):
        odds = bonus_table[mult]
        if odds and odds > 0 and rng.random() < 1.0 / odds:
            chosen = float(mult)
    return chosen


def pick_bonus_cell(winning_cells: list, rng) -> int:
    """Choose which winning (safe) cell holds the bonus — uniform among safe columns."""
    return winning_cells[rng.randrange(len(winning_cells))]


class GameCalculations(Executables):
    """Game-level calculation helpers, inheriting engine executables."""

    def get_current_mode(self) -> dict:
        """Return mode params for the current bet mode (incl. settle modes)."""
        return self.config.tower_modes[self.betmode]
