"""Tower game executables: reusable tower session actions."""

from game_calculations import (
    GameCalculations,
    generate_mine_layout,
    next_coefficient,
    pick_bonus_cell,
    roll_bonus,
)


class GameExecutables(GameCalculations):
    """Implements the tower session actions used by the gamestate.

    Randomness relies on the module-level ``random`` instance, which is
    re-seeded per simulation by ``reset_seed`` for reproducibility.

    Book sims do **not** apply bonus multipliers — settle LUTs must match the
    published ladder. Live climb uses ``session.pick_tile(..., apply_bonuses=True)``
    (and the web client) so landing on a bonus cube (e.g. ×2) multiplies the
    coefficient. Set True here only for experimental bonus-inclusive books.
    """

    # Set True only for experimental bonus-inclusive book generation.
    apply_bonuses_in_books = False

    def start_tower_session(self) -> list:
        """Generate and store the mine layout for the current bet mode."""
        mode = self.get_current_mode()
        layout = generate_mine_layout(
            mode["cols"], mode["rows"], mode["mines"], self.rng
        )
        self.tower_mines = layout
        self.tower_coefficient = 1.0
        self.tower_row_bonuses = {}  # row -> {cellIndex, multiplier} once resolved
        return layout

    def reveal_tower_tile(self, row: int, tile: int) -> dict:
        """Reveal a tile on the active row.

        Returns a dict with ``is_mine``, ``coefficient``, and optional
        ``bonus_multiplier``. Safe reveals advance the running coefficient
        by ``rowSteps[row]`` (× bonus when enabled).
        """
        mode = self.get_current_mode()
        is_mine = tile in self.tower_mines[row]
        result = {
            "is_mine": is_mine,
            "coefficient": self.tower_coefficient,
            "bonus_multiplier": None,
        }
        if is_mine:
            return result

        bonus_mult = 1.0
        if self.apply_bonuses_in_books:
            bonus_tables = mode.get("bonuses") or {}
            table = bonus_tables.get(str(row)) or bonus_tables.get(row)
            if table:
                normalised = {int(m): int(odds) for m, odds in table.items()}
                rolled = roll_bonus(normalised, self.rng)
                if rolled is not None:
                    winning = [
                        c for c in range(mode["cols"]) if c not in self.tower_mines[row]
                    ]
                    bonus_cell = pick_bonus_cell(winning, self.rng)
                    self.tower_row_bonuses[row] = {
                        "cellIndex": bonus_cell,
                        "multiplier": rolled,
                    }
                    if tile == bonus_cell:
                        bonus_mult = rolled
                        result["bonus_multiplier"] = rolled

        step = mode["rowSteps"][row]
        self.tower_coefficient = next_coefficient(
            self.tower_coefficient, step, bonus_mult
        )
        result["coefficient"] = self.tower_coefficient
        return result
